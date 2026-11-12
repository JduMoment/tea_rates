"""Для поисковиков: robots.txt и sitemap.xml.

Фронт — SPA, ссылки на чаи и магазины робот без JS не найдёт, поэтому перечисляем их в карте сайта.
"""

from datetime import datetime
from xml.sax.saxutils import escape

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from back.core.config import PUBLIC_URL
from back.enums.tea_kind import TeaKind
from back.models.catalog import Shop, Tea
from back.models.review import Review

#: Страницы без данных из БД
STATIC_PATHS = ("/", "/teas", "/shops", "/rankings", "/rankings/teas", "/rankings/shops", "/rankings/categories")

#: Личные и служебные страницы — в поиске им делать нечего
DISALLOW = (
    "/api/",
    "/login",
    "/register",
    "/forgot-password",
    "/reset-password",
    "/diary",
    "/profile",
    "/shops/new",
    "/teas/new",
)


def robots_txt() -> str:
    lines = ["User-agent: *", *(f"Disallow: {p}" for p in DISALLOW), "", f"Sitemap: {PUBLIC_URL}/sitemap.xml", ""]
    return "\n".join(lines)


class SitemapService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def entries(self) -> list[tuple[str, datetime | None]]:
        """(путь, дата последнего изменения). Дата — последний отзыв, если он есть."""
        out: list[tuple[str, datetime | None]] = [(p, None) for p in STATIC_PATHS]
        out += [(f"/rankings/categories/{k.slug}", None) for k in TeaKind]

        last_tea_review = func.max(Review.created_at)
        teas = await self.db.execute(
            select(Tea.id, func.coalesce(last_tea_review, Tea.created_at))
            .outerjoin(Review, Review.tea_id == Tea.id)
            .group_by(Tea.id)
            .order_by(Tea.id)
        )
        out += [(f"/teas/{tea_id}", changed) for tea_id, changed in teas]

        shops = await self.db.execute(
            select(Shop.name, func.max(Review.created_at))
            .outerjoin(Review, Review.shop_id == Shop.id)
            .group_by(Shop.id)
            .order_by(Shop.id)
        )
        out += [(f"/shops/{name}", changed) for name, changed in shops]

        # Профили без отзывов пустые — их не показываем
        authors = await self.db.execute(
            select(Review.user_id, func.max(Review.created_at)).group_by(Review.user_id).order_by(Review.user_id)
        )
        out += [(f"/users/{user_id}", changed) for user_id, changed in authors]
        return out

    async def xml(self) -> str:
        urls = []
        for path, changed in await self.entries():
            lastmod = f"<lastmod>{changed.date().isoformat()}</lastmod>" if changed else ""
            urls.append(f"<url><loc>{escape(PUBLIC_URL + path)}</loc>{lastmod}</url>")
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n"
        )
