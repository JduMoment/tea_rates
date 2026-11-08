"""Вьюхи, которые отдают собранный фронт (SPA на React из front/dist)."""

import mimetypes
from pathlib import Path
from typing import ClassVar

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response

from back.core.config import FRONT_DIST, MEDIA_DIR
from back.core.views import View

# Шрифты из сборки (@fontsource) и WebP-фото: стандартная таблица Python может их не знать (octet-stream)
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("image/webp", ".webp")

NOT_BUILT_HTML = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><title>Фронт не собран</title></head>
<body style="font-family: system-ui, sans-serif; max-width: 640px; margin: 64px auto; padding: 0 24px">
<h1>Фронт ещё не собран</h1>
<p>Не найден файл <code>{index}</code>.</p>
<p>Соберите его: <code>cd front &amp;&amp; npm install &amp;&amp; npm run build</code> (нужен Node 20+).</p>
</body></html>"""


class SpaView(View):
    """index.html для всех страниц фронта — дальше маршрутизирует React Router.

    Список путей повторяет роуты из front/src/App.tsx.
    """

    paths = (
        "/",
        "/teas",
        "/teas/{tea_id}",
        "/shops",
        "/shops/{shop_id}",
        "/rankings",
        "/rankings/categories",
        "/rankings/categories/{category}",
        "/rankings/shops",
        "/rankings/teas",
        # старые адреса — фронт перенаправляет на новые
        "/producers",
        "/producers/{producer_id}",
        "/rankings/producers",
        "/where-to-buy",
        "/where-to-buy/{category}",
        "/login",
        "/register",
        "/diary",
        "/profile",
        "/users/{user_id}",
    )
    include_in_schema = False
    route_options: ClassVar[dict] = {"response_class": HTMLResponse}
    #: Код ответа; NotFoundView переопределяет его на 404.
    status_code: ClassVar[int] = 200

    @staticmethod
    def index_file() -> Path:
        return FRONT_DIST / "index.html"

    async def get(self) -> Response:
        index = self.index_file()
        if not index.is_file():
            return HTMLResponse(NOT_BUILT_HTML.format(index=index), status_code=503)
        # index.html не кэшируем: после пересборки в нём новые имена бандлов
        return FileResponse(index, status_code=self.status_code, headers={"Cache-Control": "no-cache"})


class AssetView(View):
    """Бандлы Vite (/assets/index-<hash>.js|css). Имена с хэшем — кэшируем надолго."""

    paths = ("/assets/{file_path:path}",)
    include_in_schema = False
    cache_control: ClassVar[str] = "public, max-age=31536000, immutable"

    @staticmethod
    def base_dir() -> Path:
        return FRONT_DIST / "assets"

    async def get(self, file_path: str) -> FileResponse:
        base = self.base_dir().resolve()
        target = (base / file_path).resolve()
        # защита от ../ — файл обязан лежать внутри каталога
        if not target.is_relative_to(base) or not target.is_file():
            raise HTTPException(status_code=404)
        return FileResponse(target, headers={"Cache-Control": self.cache_control})


class MediaView(AssetView):
    """Загруженные файлы (фото к отзывам) из локального хранилища. Имена случайные и не меняются — кэшируем надолго."""

    paths = ("/media/{file_path:path}",)

    @staticmethod
    def base_dir() -> Path:
        return MEDIA_DIR


class PublicFileView(View):
    """Файлы из front/public, которые Vite копирует в корень dist (favicon и т.п.).

    Отдаются только явно перечисленные в paths файлы — без доступа ко всему dist.
    """

    paths = ("/favicon.svg", "/icons.svg")
    include_in_schema = False
    cache_control: ClassVar[str] = "public, max-age=86400"

    async def get(self, request: Request) -> FileResponse:
        name = request.url.path.lstrip("/")
        target = FRONT_DIST / name
        if f"/{name}" not in self.paths or not target.is_file():
            raise HTTPException(status_code=404)
        return FileResponse(target, headers={"Cache-Control": self.cache_control})


class NotFoundView(SpaView):
    """Любой другой GET-путь: отдаём SPA с кодом 404 — React покажет «Такой страницы нет».

    Неизвестные /api/* при этом остаются JSON-ошибкой.
    """

    paths = ("/{unknown_path:path}",)
    status_code = 404

    async def get(self, unknown_path: str) -> Response:  # type: ignore[override]
        if unknown_path == "api" or unknown_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        return await super().get()
