from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from back.core.config import DATABASE_URL, DB_ECHO

engine = create_async_engine(DATABASE_URL, echo=DB_ECHO, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]
