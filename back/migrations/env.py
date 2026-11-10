"""Окружение Alembic: асинхронный движок и метаданные моделей приложения."""

import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

import back.models  # noqa: F401 — регистрирует все таблицы в Base.metadata
from back.core.config import DATABASE_URL
from back.core.db import Base

target_metadata = Base.metadata


def run_offline() -> None:
    """alembic upgrade --sql: печатает SQL, не подключаясь к базе."""
    context.configure(url=DATABASE_URL, target_metadata=target_metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_online() -> None:
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    run_offline()
else:
    asyncio.run(run_online())
