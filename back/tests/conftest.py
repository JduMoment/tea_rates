"""Общие фикстуры тестов.

Тесты идут на отдельной базе tea_rates_test в том же Postgres, что и разработка
(docker compose -f deploy/docker-compose.yml up -d db). Схема в ней строится миграциями
Alembic — так тесты заодно проверяют, что миграции рабочие. Между тестами таблицы очищаются.

    poetry run pytest            # все тесты
    poetry run pytest -k photos  # только про фото
"""

import os
import shutil
import tempfile
from collections.abc import AsyncIterator
from decimal import Decimal
from pathlib import Path

# Настройки — до импорта приложения: config читает окружение один раз
TEST_DB = "tea_rates_test"
MEDIA = Path(tempfile.mkdtemp(prefix="tea_media_"))
os.environ["POSTGRES_DB"] = TEST_DB
os.environ.pop("DATABASE_URL", None)
os.environ["MEDIA_DIR"] = str(MEDIA)
os.environ["SMTP_HOST"] = ""
os.environ["PUBLIC_URL"] = "https://5listov.test"

import asyncpg
import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select, text

from back.core import config
from back.core.db import SessionFactory, engine
from back.enums.tea_kind import TeaKind
from back.main import app
from back.models import Category, DiaryEntry, Offer, Review, Shop, Tea, User

ROOT = Path(__file__).resolve().parents[2]


async def _recreate_database() -> None:
    url = config.DATABASE_URL.replace("postgresql+asyncpg", "postgresql").rsplit("/", 1)[0] + "/postgres"
    conn = await asyncpg.connect(url)
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)')
        await conn.execute(f'CREATE DATABASE "{TEST_DB}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session", autouse=True)
async def database() -> AsyncIterator[None]:
    await _recreate_database()
    # env.py Alembic сам крутит asyncio.run — запускаем его вне текущего цикла событий
    import asyncio

    await asyncio.to_thread(command.upgrade, Config(str(ROOT / "alembic.ini")), "head")
    yield
    await engine.dispose()
    shutil.rmtree(MEDIA, ignore_errors=True)


@pytest.fixture(autouse=True)
async def clean() -> AsyncIterator[None]:
    """Каждый тест — с чистыми таблицами (кроме справочника видов чая из миграции)."""
    yield
    async with engine.begin() as conn:
        tables = [
            t
            for t in (await conn.execute(text("select tablename from pg_tables where schemaname = 'public'"))).scalars()
            if t not in ("categories", "alembic_version")
        ]
        await conn.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))
    for child in MEDIA.iterdir():
        shutil.rmtree(child, ignore_errors=True) if child.is_dir() else child.unlink()


# ---------- HTTP ----------


def new_client() -> httpx.AsyncClient:
    """Отдельный «браузер» со своими cookie — для сценариев с несколькими пользователями."""
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with new_client() as c:
        yield c


async def register(
    c: httpx.AsyncClient, name: str = "Иван", email: str = "ivan@example.com", password: str = "secret1"
):
    r = await c.post("/api/auth/register", json={"name": name, "email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
async def user(client: httpx.AsyncClient) -> dict:
    """Зарегистрированный и вошедший пользователь (cookie в client)."""
    return await register(client)


@pytest.fixture
async def other() -> AsyncIterator[tuple[httpx.AsyncClient, dict]]:
    """Второй пользователь со своим клиентом."""
    async with new_client() as c:
        yield c, await register(c, "Мария", "maria@example.com")


# ---------- данные каталога ----------


async def make_shop(name: str = "daochain", title: str = "DaoChain", site: str | None = None) -> int:
    async with SessionFactory() as db:
        shop = Shop(name=name, title=title, country="Россия", city="Москва", site=site or f"https://{name}.example")
        db.add(shop)
        await db.commit()
        return shop.id


async def make_tea(
    title: str, kind: TeaKind = TeaKind.RED, shops: list[int] = (), price: int | None = None, weight: int = 50
) -> int:
    async with SessionFactory() as db:
        category = await db.scalar(select(Category).where(Category.name == kind))
        tea = Tea(category_id=category.id, name=title.lower().replace(" ", "-"), title=title, description="")
        db.add(tea)
        await db.flush()
        for shop_id in shops:
            db.add(
                Offer(
                    tea_id=tea.id,
                    shop_id=shop_id,
                    start_price=price,
                    start_weight=weight if price else None,
                )
            )
        await db.commit()
        return tea.id


async def add_review(
    user_id: int, tea_id: int, shop_id: int, rating: int, flavors: list = (), price: int | None = None, **infusion
):
    """Отзыв напрямую в базу — когда важны данные, а не путь через API."""
    async with SessionFactory() as db:
        db.add(
            Review(
                user_id=user_id,
                tea_id=tea_id,
                shop_id=shop_id,
                rating=rating,
                text="Тестовый отзыв",
                flavors=list(flavors),
                price=price,
                weight=50 if price else None,
                **infusion,
            )
        )
        await db.commit()


async def add_user(email: str, name: str = "Автор") -> int:
    async with SessionFactory() as db:
        u = User(name=name, email=email, password_hash="!")
        db.add(u)
        await db.commit()
        return u.id


async def add_diary(user_id: int, tea_id: int, shop_id: int, **fields) -> None:
    params = {"rating": 4, "water": 90, "grams": Decimal(5), "volume": 100, "infusions": 6, "text": ""} | fields
    from datetime import date

    async with SessionFactory() as db:
        db.add(DiaryEntry(user_id=user_id, tea_id=tea_id, shop_id=shop_id, date=date(2026, 10, 1), **params))
        await db.commit()
