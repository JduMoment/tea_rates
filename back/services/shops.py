"""Пользователи добавляют магазины сами — значит, главное здесь не дать завести дубль.

Два уровня защиты:
1. Сайт. Ключ сайта (core/shop_url.py) уникален в БД: «https://www.shop.ru/catalog» и «shop.ru» —
   один магазин, второй раз его не создать ни через форму, ни гонкой двух запросов.
2. Название. Похожие названия (с учётом транслита: «Арт оф Ти» ≈ «Art of Tea») не запрещаем —
   у разных магазинов бывают похожие имена, — но показываем их в форме до создания.
"""

from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from back.core.shop_url import BadShopUrl, shop_key
from back.core.slug import slugify, unique_slug
from back.models import Shop, User
from back.services.errors import ConflictError

#: Порог похожести названий (0–1) после транслита и удаления пробелов и знаков.
SIMILAR_RATIO = 0.75
SIMILAR_LIMIT = 5


class ShopExistsError(ConflictError):
    def __init__(self, existing: Shop) -> None:
        super().__init__(f"Магазин с этим сайтом уже есть — «{existing.title}»")
        self.existing = existing


@dataclass(frozen=True, slots=True)
class ShopCheck:
    #: Ключ сайта или текст ошибки, если адрес не разобрать.
    site_key: str | None
    site_error: str | None
    #: Магазин с тем же сайтом — создать такой же нельзя.
    same_site: Shop | None
    #: Магазины с похожим названием — стоит проверить глазами.
    similar: list[Shop]


def _norm(title: str) -> str:
    return slugify(title, 128).replace("-", "")


def similar_titles(title: str, shops: list[Shop]) -> list[Shop]:
    needle = _norm(title)
    if len(needle) < 3:
        return []
    scored = []
    for shop in shops:
        other = _norm(shop.title)
        ratio = SequenceMatcher(None, needle, other).ratio()
        if ratio >= SIMILAR_RATIO or (len(needle) >= 4 and (needle in other or other in needle)):
            scored.append((ratio, shop))
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:SIMILAR_LIMIT]]


class ShopEditorService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def check(self, title: str = "", site: str = "") -> ShopCheck:
        key = error = None
        same = None
        if site.strip():
            try:
                key = shop_key(site)
            except BadShopUrl as exc:
                error = str(exc)
        if key:
            same = await self.db.scalar(select(Shop).where(Shop.site_key == key))
        similar = similar_titles(title, list(await self.db.scalars(select(Shop)))) if title.strip() else []
        if same:
            similar = [s for s in similar if s.id != same.id]
        return ShopCheck(site_key=key, site_error=error, same_site=same, similar=similar)

    async def create(
        self, user: User, *, title: str, site: str, city: str, country: str, description: str | None
    ) -> Shop:
        existing = await self.db.scalar(select(Shop).where(Shop.site_key == shop_key(site)))
        if existing:
            raise ShopExistsError(existing)
        taken = set(await self.db.scalars(select(Shop.name)))
        shop = Shop(
            name=unique_slug(title, taken),
            title=title,
            site=site,
            city=city,
            country=country,
            description=description,
            author_id=user.id,
        )
        self.db.add(shop)
        try:
            await self.db.commit()
        except IntegrityError:
            # Кто-то успел добавить тот же сайт между проверкой и записью — уникальный ключ в БД поймал
            await self.db.rollback()
            existing = await self.db.scalar(select(Shop).where(Shop.site_key == shop_key(site)))
            raise ShopExistsError(existing) from None
        return shop
