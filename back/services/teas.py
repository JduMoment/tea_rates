"""Пользователи пополняют каталог: добавляют чаи и магазины, где их купить.

Модерации пока нет: добавленное видно сразу. Править и удалять может только автор
и только пока на это нет чужих отзывов — чтобы нельзя было «переименовать» чай под чужими оценками.
Новые магазины пользователи не заводят — только выбирают из существующих.
"""

from dataclasses import asdict, dataclass

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from back.core.slug import slugify, unique_slug
from back.models import Offer, Review, Tea, User
from back.services.catalog import CatalogService, TeaDetails
from back.services.errors import LastOfferError, OfferExistsError, OfferLockedError, TeaExistsError, TeaLockedError


@dataclass(frozen=True, slots=True)
class OfferFields:
    """Магазин продаёт чай: ссылка и цена на момент добавления (дальше цену обновляют отзывы)."""

    price: int | None = None
    weight: int | None = None
    url: str | None = None

    def columns(self) -> dict:
        """Поля модели Offer."""
        return {"start_price": self.price, "start_weight": self.weight, "url": self.url}


@dataclass(frozen=True, slots=True)
class TeaFields:
    title: str
    region: str | None = None
    description: str = ""


class TeaEditorService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.catalog = CatalogService(db)

    # ---------- чай ----------

    async def create(
        self, user: User, *, category_slug: str, tea: TeaFields, shop_id: int, offer: OfferFields
    ) -> TeaDetails:
        """Новый чай сразу с первым магазином, где его продают."""
        category = await self.catalog.category(category_slug)
        shop = await self.catalog.get_shop_by_id(shop_id)
        if await self._title_taken(category.id, tea.title):
            raise TeaExistsError
        new = Tea(
            category=category,
            name=await self._free_name(tea.title),
            author_id=user.id,
            **asdict(tea),
        )
        new.add_offer(shop, author_id=user.id, **offer.columns())
        self.db.add(new)
        await self._commit(TeaExistsError)
        return await self.catalog.tea(new.id)

    async def update(self, user: User, tea_id: int, fields: TeaFields) -> TeaDetails:
        tea = await self.catalog.get_tea(tea_id)
        await self._check_editable(user, tea)
        if fields.title.casefold() != tea.title.casefold() and await self._title_taken(tea.category_id, fields.title):
            raise TeaExistsError
        for attr, value in asdict(fields).items():
            setattr(tea, attr, value)
        await self._commit(TeaExistsError)
        return await self.catalog.tea(tea.id)

    async def delete(self, user: User, tea_id: int) -> None:
        tea = await self.catalog.get_tea(tea_id)
        await self._check_editable(user, tea)
        await self.db.delete(tea)
        await self.db.commit()

    # ---------- магазины чая ----------

    async def add_offer(self, user: User, tea_id: int, shop_id: int, fields: OfferFields) -> TeaDetails:
        """«Этот чай есть ещё и в таком-то магазине»."""
        tea = await self.catalog.get_tea(tea_id)
        shop = await self.catalog.get_shop_by_id(shop_id)
        if any(o.shop_id == shop.id for o in tea.offers):
            raise OfferExistsError
        self.db.add(tea.add_offer(shop, author_id=user.id, **fields.columns()))
        await self._commit(OfferExistsError)
        return await self.catalog.tea(tea.id)

    async def update_offer(self, user: User, tea_id: int, shop_id: int, fields: OfferFields) -> TeaDetails:
        offer = await self.catalog.get_offer(tea_id, shop_id)
        await self._check_offer_editable(user, offer)
        for attr, value in fields.columns().items():
            setattr(offer, attr, value)
        await self.db.commit()
        return await self.catalog.tea(tea_id)

    async def delete_offer(self, user: User, tea_id: int, shop_id: int) -> None:
        offer = await self.catalog.get_offer(tea_id, shop_id)
        await self._check_offer_editable(user, offer)
        tea = await self.catalog.get_tea(tea_id)
        if len(tea.offers) == 1:
            raise LastOfferError
        await self.db.delete(offer)
        await self.db.commit()

    # ---------- проверки ----------

    async def _check_editable(self, user: User, tea: Tea) -> None:
        foreign = exists().where(Review.tea_id == tea.id, Review.user_id != user.id)
        if not user.created(tea) or await self.db.scalar(select(foreign)):
            raise TeaLockedError

    async def _check_offer_editable(self, user: User, offer: Offer) -> None:
        foreign = exists().where(
            Review.tea_id == offer.tea_id, Review.shop_id == offer.shop_id, Review.user_id != user.id
        )
        if not user.created(offer) or await self.db.scalar(select(foreign)):
            raise OfferLockedError

    async def _title_taken(self, category_id: int, title: str) -> bool:
        same = exists().where(Tea.category_id == category_id, func.lower(Tea.title) == title.lower())
        return bool(await self.db.scalar(select(same)))

    async def _free_name(self, title: str) -> str:
        base = slugify(title, 60)
        taken = set(await self.db.scalars(select(Tea.name).where(Tea.name.startswith(base, autoescape=True))))
        return unique_slug(title, taken)

    async def _commit(self, on_conflict: type[Exception]) -> None:
        """Коммит; гонка двух одинаковых добавлений упирается в уникальный индекс — это тот же конфликт."""
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise on_conflict from exc
