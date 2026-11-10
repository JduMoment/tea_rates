"""Фото к отзывам: проверяем, что это картинка, поворачиваем по EXIF, уменьшаем и пересохраняем в WebP.

Пересохранение выбрасывает все метаданные (EXIF с геопозицией, модель телефона) — их в исходный файл
кладёт камера, а публиковать их незачем. Хранятся две версии: большая и превью для ленты.
"""

import secrets
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from back.core.storage import storage
from back.models import Review, ReviewPhoto, User
from back.services.errors import ConflictError, ReviewNotFoundError

MAX_PHOTOS = 3
MAX_BYTES = 10 * 1024 * 1024
MAX_SIDE = 1600
THUMB_SIDE = 480
FORMATS = {"JPEG", "PNG", "WEBP"}
# Защита от «бомб»: картинка 20000×20000 в маленьком файле съела бы всю память при распаковке
Image.MAX_IMAGE_PIXELS = 50_000_000


class PhotoError(ValueError):
    """Файл не подходит — текст ошибки показываем пользователю."""


class TooManyPhotosError(ConflictError):
    message = f"К отзыву — не больше {MAX_PHOTOS} фото"


@dataclass(frozen=True, slots=True)
class Processed:
    big: bytes
    thumb: bytes
    width: int
    height: int


def decode(data: bytes) -> Image.Image:
    """Проверяет, что это JPEG/PNG/WebP не больше MAX_BYTES, и поворачивает по EXIF."""
    if len(data) > MAX_BYTES:
        raise PhotoError("Файл больше 10 МБ")
    try:
        with Image.open(BytesIO(data)) as probe:
            fmt = probe.format
            probe.verify()
        img = Image.open(BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise PhotoError("Это не похоже на фото — подойдут JPEG, PNG или WebP") from exc
    if fmt not in FORMATS:
        raise PhotoError("Подойдут JPEG, PNG или WebP")
    return ImageOps.exif_transpose(img)


def to_webp(img: Image.Image, side: int, *, keep_alpha: bool = False) -> tuple[bytes, int, int]:
    """Вписывает в квадрат side×side и пересохраняет в WebP. keep_alpha — для логотипов с прозрачным фоном."""
    transparent = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    copy = img.convert("RGBA" if keep_alpha and transparent else "RGB")
    copy.thumbnail((side, side), Image.Resampling.LANCZOS)
    out = BytesIO()
    copy.save(out, "WEBP", quality=82, method=4)  # без exif= — метаданные не сохраняются
    return out.getvalue(), copy.width, copy.height


def process(data: bytes) -> Processed:
    img = decode(data)
    big, width, height = to_webp(img, MAX_SIDE)
    thumb, _, _ = to_webp(img, THUMB_SIDE)
    return Processed(big=big, thumb=thumb, width=width, height=height)


class PhotoService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _own_review(self, user: User, review_id: int) -> Review:
        review = await self.db.get(Review, review_id)
        if not review or not user.owns(review):
            raise ReviewNotFoundError
        return review

    async def add(self, user: User, review_id: int, data: bytes) -> Review:
        review = await self._own_review(user, review_id)
        count = await self.db.scalar(select(func.count()).where(ReviewPhoto.review_id == review_id))
        if count >= MAX_PHOTOS:
            raise TooManyPhotosError
        processed = await run_in_threadpool(process, data)
        name = secrets.token_hex(8)
        key, thumb_key = f"reviews/{review_id}/{name}.webp", f"reviews/{review_id}/{name}-thumb.webp"
        storage.save(key, processed.big)
        storage.save(thumb_key, processed.thumb)
        self.db.add(
            ReviewPhoto(
                review_id=review_id,
                position=count,
                key=key,
                thumb_key=thumb_key,
                width=processed.width,
                height=processed.height,
            )
        )
        await self.db.commit()
        await self.db.refresh(review, ["photos"])
        return review

    async def delete(self, user: User, review_id: int, photo_id: int) -> None:
        await self._own_review(user, review_id)
        photo = await self.db.get(ReviewPhoto, photo_id)
        if not photo or photo.review_id != review_id:
            raise ReviewNotFoundError("Фото не найдено")
        await self.db.delete(photo)
        await self.db.commit()
        remove_files([photo])


def remove_files(photos: list[ReviewPhoto]) -> None:
    for p in photos:
        storage.delete(p.key)
        storage.delete(p.thumb_key)
