"""Схема БД: миграции совпадают с моделями, справочник видов чая на месте."""

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from back.core.db import Base, engine


async def test_migrations_match_models():
    """Если тест упал — модели поменяли, а миграцию не создали: alembic revision --autogenerate."""
    async with engine.connect() as conn:
        diff = await conn.run_sync(
            lambda c: compare_metadata(MigrationContext.configure(c, opts={"compare_type": True}), Base.metadata)
        )
    assert diff == []


async def test_categories_seeded_by_migration(client):
    r = await client.get("/api/categories")
    assert r.status_code == 200
    assert {c["slug"] for c in r.json()} == {
        "green",
        "white",
        "yellow",
        "oolong",
        "gaba",
        "red",
        "shu",
        "sheng",
        "heicha",
        "herbal",
    }


async def test_health(client):
    assert (await client.get("/api/health")).json() == {"status": "ok"}
