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

# --- почта (восстановление пароля) ---
#: SMTP-сервер. Пусто — письма не отправляются, а пишутся в лог бэкенда (удобно при разработке).
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
#: Шифрование: ssl (порт 465) или starttls (порт 587).
SMTP_SECURITY = os.getenv("SMTP_SECURITY", "ssl")
#: Отправитель: «5 листов <noreply@5listov.ru>».
MAIL_FROM = os.getenv("MAIL_FROM", "5 листов <noreply@5listov.ru>")
#: Куда слать письма об ошибках на сайте (см. core/logs.py). Пусто — не слать, ошибки только в логе.
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "")
#: Сколько живёт ссылка для сброса пароля.
PASSWORD_RESET_TTL_MINUTES = int(os.getenv("PASSWORD_RESET_TTL_MINUTES", "60"))
