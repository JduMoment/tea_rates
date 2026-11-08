"""Настройки приложения. Берутся из переменных окружения и файла .env в корне проекта.

Список переменных с пояснениями — в .env.example.
"""

import os
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]

# Уже заданные переменные окружения (например, из docker-compose) имеют приоритет над .env
load_dotenv(BASE_DIR / ".env")


class ConfigError(RuntimeError):
    pass


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigError(f"Не задана переменная {name}. Скопируйте .env.example в .env и заполните его.")
    return value


def _database_url() -> str:
    """DATABASE_URL целиком, либо собирается из POSTGRES_* (их же читает контейнер Postgres)."""
    if url := os.getenv("DATABASE_URL"):
        return url
    user = quote(_required("POSTGRES_USER"), safe="")
    password = quote(_required("POSTGRES_PASSWORD"), safe="")
    db = _required("POSTGRES_DB")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5433")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


#: Каталог со сборкой фронта (результат `npm run build` в front/).
FRONT_DIST = Path(os.getenv("FRONT_DIST", BASE_DIR / "front" / "dist")).resolve()

#: Подключение к Postgres (драйвер asyncpg).
DATABASE_URL = _database_url()
DB_ECHO = os.getenv("DB_ECHO", "0") == "1"

# --- сессии ---
SESSION_COOKIE = os.getenv("SESSION_COOKIE", "tea_session")
SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "30"))
#: В проде за HTTPS обязательно включить (COOKIE_SECURE=1).
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "0") == "1"

# --- вход через внешних провайдеров (OAuth) ---
#: Адрес сайта снаружи, без слэша в конце. Из него собираются redirect URI,
#: которые должны совпадать с указанными в кабинете провайдера.
PUBLIC_URL = os.getenv("PUBLIC_URL", "http://localhost:8000").rstrip("/")
#: Яндекс ID (https://oauth.yandex.ru). Пустые — кнопка входа отвечает «недоступно».
YANDEX_CLIENT_ID = os.getenv("YANDEX_CLIENT_ID", "")
YANDEX_CLIENT_SECRET = os.getenv("YANDEX_CLIENT_SECRET", "")

# --- загруженные файлы (фото к отзывам) ---
#: Куда складывать файлы. В Docker — отдельный том (см. deploy/docker-compose.yml), чтобы пережили пересборку.
MEDIA_DIR = Path(os.getenv("MEDIA_DIR", BASE_DIR / "media")).resolve()
#: Префикс адресов файлов. Если позже переедем в облако (S3) — сюда пойдёт адрес бакета или CDN.
MEDIA_URL = os.getenv("MEDIA_URL", "/media").rstrip("/")
