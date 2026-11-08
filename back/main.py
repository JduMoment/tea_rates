from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from back.core.db import engine
from back.routes import ROUTES
from back.services.errors import ConflictError, ForbiddenError, NotFoundError


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Таблицы при старте больше не создаём — схемой будут управлять миграции (Alembic)
    yield
    await engine.dispose()


app = FastAPI(
    title="tea_rates",
    lifespan=lifespan,
)


@app.exception_handler(NotFoundError)
async def not_found(_: Request, exc: NotFoundError) -> JSONResponse:
    """Сервисы бросают NotFoundError — вьюхам не нужно ловить его в каждом методе."""
    return JSONResponse({"detail": str(exc)}, status_code=status.HTTP_404_NOT_FOUND)


@app.exception_handler(ConflictError)
async def conflict(_: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=status.HTTP_409_CONFLICT)


@app.exception_handler(ForbiddenError)
async def forbidden(_: Request, exc: ForbiddenError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=status.HTTP_403_FORBIDDEN)


for routes_cls in ROUTES:
    app.include_router(routes_cls().router)
