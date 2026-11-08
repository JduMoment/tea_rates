"""Оценки и их агрегаты: средняя по чаю, по предложению, по магазину, по магазину внутри вида чая.

Чай оценивается по всем отзывам (из любых магазинов), магазин — по отзывам на чаи,
купленные у него (Review.shop_id), число чаёв магазина — по его предложениям (offers).

Средние считает Postgres (GROUP BY), а сглаживание и сортировка — здесь, в Python:
формулу проще менять и тестировать в одном месте.
"""

from dataclasses import dataclass
from typing import ClassVar

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from back.models import Offer, Review, Tea


@dataclass(frozen=True, slots=True)
class Score:
    """Средняя оценка и число отзывов, на которых она основана."""

    #: Сглаживание: оценка с малым числом отзывов подтягивается к PRIOR_MEAN,
    #: как будто у неё есть ещё PRIOR_WEIGHT «средних» отзывов.
    #: Так одна случайная пятёрка не выводит чай или магазин в лидеры.
    PRIOR_MEAN: ClassVar[float] = 3.5
    PRIOR_WEIGHT: ClassVar[int] = 2
    #: Порог «фирменного» вида чая у магазина.
    SPECIALTY_MIN_REVIEWS: ClassVar[int] = 3
    SPECIALTY_MIN_WEIGHTED: ClassVar[float] = 4.2

    avg: float = 0.0
    reviews: int = 0

    @property
    def weighted(self) -> float:
        """Сглаженная оценка — по ней сортируем рейтинги."""
        return (self.avg * self.reviews + self.PRIOR_MEAN * self.PRIOR_WEIGHT) / (self.reviews + self.PRIOR_WEIGHT)

    @property
    def is_specialty(self) -> bool:
        return self.reviews >= self.SPECIALTY_MIN_REVIEWS and self.weighted >= self.SPECIALTY_MIN_WEIGHTED

    @classmethod
    def of(cls, avg: float | None, reviews: int | None) -> "Score":
        return cls(avg=float(avg or 0), reviews=int(reviews or 0))


EMPTY_SCORE = Score()


@dataclass(frozen=True, slots=True)
class ShopCategoryScore:
    """Как магазину удаётся определённый вид чая: средняя по отзывам на его чаи этого вида."""

    shop_id: int
    category_id: int
    score: Score
    teas: int


@dataclass(frozen=True, slots=True)
class ShopScore:
    """Общая оценка магазина по всем его чаям."""

    score: Score
    teas: int


class ScoreRepository:
    """Агрегирующие запросы по отзывам. Каждый метод — один SQL-запрос."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def for_teas(self, tea_ids: list[int] | None = None) -> dict[int, Score]:
        """Оценки чаёв. Чаёв без отзывов в словаре нет — используйте .get(id, EMPTY_SCORE)."""
        query = select(Review.tea_id, func.avg(Review.rating), func.count(Review.id)).group_by(Review.tea_id)
        if tea_ids is not None:
            if not tea_ids:
                return {}
            query = query.where(Review.tea_id.in_(tea_ids))
        rows = await self.db.execute(query)
        return {tea_id: Score.of(avg, n) for tea_id, avg, n in rows}

    async def for_offers(
        self, *, tea_ids: list[int] | None = None, category_id: int | None = None
    ) -> dict[tuple[int, int], Score]:
        """Оценки чаёв в конкретных магазинах: (tea_id, shop_id) → Score. Без отзывов — нет в словаре."""
        query = select(Review.tea_id, Review.shop_id, func.avg(Review.rating), func.count(Review.id)).group_by(
            Review.tea_id, Review.shop_id
        )
        if tea_ids is not None:
            if not tea_ids:
                return {}
            query = query.where(Review.tea_id.in_(tea_ids))
        if category_id is not None:
            query = query.join(Tea, Tea.id == Review.tea_id).where(Tea.category_id == category_id)
        rows = await self.db.execute(query)
        return {(tea_id, shop_id): Score.of(avg, n) for tea_id, shop_id, avg, n in rows}

    async def by_shop_and_category(
        self, *, shop_id: int | None = None, category_id: int | None = None
    ) -> list[ShopCategoryScore]:
        """Оценки «магазин × вид чая». Виды, где у магазина есть чаи без отзывов, тоже попадают (с нулём)."""
        query = (
            select(
                Offer.shop_id,
                Tea.category_id,
                func.count(distinct(Offer.tea_id)),
                func.count(Review.id),
                func.avg(Review.rating),
            )
            .join(Tea, Tea.id == Offer.tea_id)
            .outerjoin(Review, (Review.tea_id == Offer.tea_id) & (Review.shop_id == Offer.shop_id))
            .group_by(Offer.shop_id, Tea.category_id)
        )
        if shop_id is not None:
            query = query.where(Offer.shop_id == shop_id)
        if category_id is not None:
            query = query.where(Tea.category_id == category_id)
        rows = await self.db.execute(query)
        return [
            ShopCategoryScore(shop_id=s, category_id=c, score=Score.of(avg, n), teas=teas)
            for s, c, teas, n, avg in rows
        ]

    async def by_shop(self) -> dict[int, ShopScore]:
        """Общая оценка каждого магазина, у которого есть хоть один чай."""
        query = (
            select(Offer.shop_id, func.count(distinct(Offer.tea_id)), func.count(Review.id), func.avg(Review.rating))
            .outerjoin(Review, (Review.tea_id == Offer.tea_id) & (Review.shop_id == Offer.shop_id))
            .group_by(Offer.shop_id)
        )
        rows = await self.db.execute(query)
        return {shop_id: ShopScore(score=Score.of(avg, n), teas=teas) for shop_id, teas, n, avg in rows}


def best_first[T](items: list[T], score_of) -> list[T]:
    """Сортировка по сглаженной оценке, лучшие первыми."""
    return sorted(items, key=lambda item: score_of(item).weighted, reverse=True)
