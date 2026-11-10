import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from back.core.auth import SessionCookie
from back.core.db import SessionFactory, engine
from back.core.logs import setup_logging
from back.routes import ROUTES
from back.services.auth import AuthService
from back.services.errors import ConflictError, ForbiddenError, NotFoundError

setup_logging()
log = logging.getLogger("back.errors")


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


async def _user_id(request: Request) -> int | None:
    """Кто был в упавшем запросе — по cookie сессии. Если не вышло (лежит база) — None."""
    try:
        async with SessionFactory() as db:
            user = await AuthService(db).user_by_token(SessionCookie.read(request))
            return user.id if user else None
    except Exception:  # noqa: BLE001 — в письмо об ошибке пойдёт «не вошёл», это не повод падать ещё раз
        return None


@app.middleware("http")
async def unhandled_errors(request: Request, call_next):
    """Необработанная ошибка: в лог (а оттуда письмом) — с адресом и пользователем; клиенту — 500 без подробностей."""
    try:
        return await call_next(request)
    except Exception:
        user_id = getattr(request.state, "user_id", None) or await _user_id(request)
        query = f"?{request.url.query}" if request.url.query else ""
        log.exception("%s %s%s — пользователь %s", request.method, request.url.path, query, user_id or "не вошёл")
        return JSONResponse({"detail": "Что-то сломалось на сервере. Мы уже знаем и чиним."}, status_code=500)


for routes_cls in ROUTES:
    app.include_router(routes_cls().router)
