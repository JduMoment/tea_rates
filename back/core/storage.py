"""Хранилище загруженных файлов. Сейчас — диск сервера (Docker-том); интерфейс рассчитан на то,
чтобы позже подменить реализацию на объектное хранилище (Yandex Object Storage / S3), не трогая остальной код."""

from pathlib import Path
from typing import Protocol

from back.core.config import MEDIA_DIR, MEDIA_URL


class Storage(Protocol):
    def save(self, key: str, data: bytes) -> None: ...
    def delete(self, key: str) -> None: ...
    def url(self, key: str) -> str: ...


class LocalStorage:
    """Файлы на диске: ключ «reviews/12/ab3f.webp» → MEDIA_DIR/reviews/12/ab3f.webp, адрес /media/reviews/12/ab3f.webp."""

    def __init__(self, root: Path, base_url: str) -> None:
        self.root = root
        self.base_url = base_url

    def path(self, key: str) -> Path:
        target = (self.root / key).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError(f"Ключ вне хранилища: {key}")
        return target

    def save(self, key: str, data: bytes) -> None:
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(target)  # атомарно: недописанный файл никто не увидит

    def delete(self, key: str) -> None:
        self.path(key).unlink(missing_ok=True)

    def url(self, key: str) -> str:
        return f"{self.base_url}/{key}"


storage: Storage = LocalStorage(MEDIA_DIR, MEDIA_URL)
