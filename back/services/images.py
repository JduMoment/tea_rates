"""Картинки каталога: фото чая и логотип магазина. Необязательны.

Поставить картинку может любой вошедший пользователь, пока её нет (обычно — автор сразу при добавлении).
Заменить или удалить загруженную нельзя никому.
Обработка та же, что у фото к отзывам (back.services.photos): проверка формата, EXIF-поворот, WebP без метаданных.
"""

import secrets
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from back.core.storage import storage
from back.services.catalog import CatalogService
from back.services.errors import ForbiddenError
from back.services.photos import decode, to_webp

TEA_SIDE = 1200
TEA_THUMB_SIDE = 480
LOGO_SIDE = 256


class ImageLockedError(ForbiddenError):
    message = "Картинка уже есть — заменить её нельзя"


@dataclass(frozen=True, slots=True)
class StoredImage:
    url: str
    thumb_url: str


def _tea_variants(data: bytes) -> tuple[bytes, bytes]:
    img = decode(data)
    return to_webp(img, TEA_SIDE)[0], to_webp(img, TEA_THUMB_SIDE)[0]


def _logo(data: bytes) -> bytes:
    return to_webp(decode(data), LOGO_SIDE, keep_alpha=True)[0]


def _check(current: str | None) -> None:
    if current:
        raise ImageLockedError


class CatalogImageService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.catalog = CatalogService(db)

    async def set_tea_image(self, tea_id: int, data: bytes) -> StoredImage:
        tea = await self.catalog.get_tea(tea_id)
        _check(tea.image_key)
        big, thumb = await run_in_threadpool(_tea_variants, data)
        name = secrets.token_hex(8)
        key, thumb_key = f"teas/{tea.id}/{name}.webp", f"teas/{tea.id}/{name}-thumb.webp"
        storage.save(key, big)
        storage.save(thumb_key, thumb)
        tea.image_key, tea.image_thumb_key = key, thumb_key
        await self.db.commit()
        return StoredImage(url=storage.url(key), thumb_url=storage.url(thumb_key))

    async def set_shop_logo(self, shop_id: int, data: bytes) -> StoredImage:
        shop = await self.catalog.get_shop_by_id(shop_id)
        _check(shop.logo_key)
        logo = await run_in_threadpool(_logo, data)
        key = f"shops/{shop.id}/{secrets.token_hex(8)}.webp"
        storage.save(key, logo)
        shop.logo_key = key
        await self.db.commit()
        return StoredImage(url=storage.url(key), thumb_url=storage.url(key))
