"""Вьюхи, которые отдают собранный фронт (SPA на React из front/dist)."""

import html
import mimetypes
import re
from pathlib import Path
from typing import ClassVar

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response

from back.core.config import FRONT_DIST, MEDIA_DIR, PUBLIC_URL
from back.core.db import DbSession
from back.core.views import View
from back.services.previews import DEFAULT, SITE, Preview, PreviewService, cached_render

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
        "/shops/new",
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
        "/forgot-password",
        "/reset-password",
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

    async def get(self, request: Request, db: DbSession) -> Response:
        index = self.index_file()
        if not index.is_file():
            return HTMLResponse(NOT_BUILT_HTML.format(index=index), status_code=503)
        # Превью для мессенджеров и поисковиков: они не выполняют JS, поэтому теги вставляем на сервере
        preview = DEFAULT if self.status_code == 404 else await PreviewService(db).for_path(request.url.path)
        page = with_preview(index.read_text(encoding="utf-8"), preview, request.url.path)
        # index.html не кэшируем: после пересборки в нём новые имена бандлов
        return HTMLResponse(page, status_code=self.status_code, headers={"Cache-Control": "no-cache"})


def with_preview(page: str, p: Preview, path: str) -> str:
    """Подставляет в index.html заголовок и теги Open Graph / Twitter."""
    e = lambda v: html.escape(v, quote=True)
    url, image = f"{PUBLIC_URL}{path}", f"{PUBLIC_URL}{p.image}"
    tags = "\n".join(
        [
            f'<meta name="description" content="{e(p.description)}" />',
            f'<meta property="og:site_name" content="{SITE}" />',
            '<meta property="og:locale" content="ru_RU" />',
            '<meta property="og:type" content="website" />',
            f'<meta property="og:url" content="{e(url)}" />',
            f'<meta property="og:title" content="{e(p.title)}" />',
            f'<meta property="og:description" content="{e(p.description)}" />',
            f'<meta property="og:image" content="{e(image)}" />',
            '<meta property="og:image:width" content="1200" />',
            '<meta property="og:image:height" content="630" />',
            '<meta name="twitter:card" content="summary_large_image" />',
            f'<link rel="canonical" href="{e(url)}" />',
        ]
    )
    page = re.sub(r"<title>.*?</title>", f"<title>{e(p.title)}</title>", page, count=1, flags=re.DOTALL)
    return page.replace("</head>", f"{tags}\n</head>", 1)


class OgImageView(View):
    """Картинка 1200×630 для превью ссылки: /og/default.png, /og/teas/12.png, /og/shops/daochain.png, /og/users/3.png."""

    paths = ("/og/default.png", "/og/teas/{tea_id}.png", "/og/shops/{name}.png", "/og/users/{user_id}.png")
    include_in_schema = False

    async def get(self, request: Request, db: DbSession) -> Response:
        path = request.url.path.removeprefix("/og").removesuffix(".png")
        if path == "/default":
            preview = DEFAULT
        else:
            preview = await PreviewService(db).for_path(path)
            if preview is DEFAULT:
                raise HTTPException(status_code=404)
        return Response(
            cached_render(path, preview), media_type="image/png", headers={"Cache-Control": "public, max-age=3600"}
        )


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

    async def get(self, unknown_path: str, request: Request, db: DbSession) -> Response:  # type: ignore[override]
        if unknown_path == "api" or unknown_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        return await super().get(request, db)
