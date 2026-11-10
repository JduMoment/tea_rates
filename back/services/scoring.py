"""Оценки и их агрегаты: средняя по чаю, по предложению, по магазину, по магазину внутри вида чая.

Чай оценивается по всем отзывам (из любых магазинов), магазин — по отзывам на чаи,
купленные у него (Review.shop_id), число чаёв магазина — по его предложениям (offers).

Все оценки учитывают, кто их ставил (см. ReviewWeighting), — чтобы низкосортный чай и магазин
с таким чаем не обходили хорошие за счёт пятёрок от тех, кто чая пробовал мало или ставит 5 всему подряд:
- вес отзыва растёт с опытом автора — числом разных чаёв, которые он оценил;
- из оценки вычитается щедрость автора — насколько его средняя выше средней по сайту.
Число отзывов (Score.reviews) при этом честное — сколько их написано.

Средние считает Postgres (GROUP BY), а сглаживание и сортировка — здесь, в Python:
формулу проще менять и тестировать в одном месте.
"""

from dataclasses import dataclass
from typing import ClassVar

from sqlalchemy import distinct, func, literal, select
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
    #: Сумма весов отзывов. None — все отзывы весят 1 (тогда это просто reviews).
    weight_sum: float | None = None

    @property
    def mass(self) -> float:
        """Сколько «полновесных» отзывов стоит за оценкой."""
        return self.reviews if self.weight_sum is None else self.weight_sum

    @property
    def weighted(self) -> float:
        """Сглаженная оценка — по ней сортируем рейтинги."""
        return (self.avg * self.mass + self.PRIOR_MEAN * self.PRIOR_WEIGHT) / (self.mass + self.PRIOR_WEIGHT)

    @property
    def shown(self) -> float:
        """Оценка для показа на сайте — сглаженная, чтобы цифры совпадали с порядком в рейтингах.
        Без отзывов — 0 (а не PRIOR_MEAN): фронт по reviews пишет «пока без отзывов»."""
        return self.weighted if self.reviews else 0.0

    @property
    def is_specialty(self) -> bool:
        return self.reviews >= self.SPECIALTY_MIN_REVIEWS and self.weighted >= self.SPECIALTY_MIN_WEIGHTED

    @classmethod
    def of(cls, avg: float | None, reviews: int | None, weight_sum: float | None = None) -> "Score":
        return cls(
            avg=float(avg or 0),
            reviews=int(reviews or 0),
            weight_sum=None if weight_sum is None else float(weight_sum),
        )

    @classmethod
    def combine(cls, scores: list["Score"]) -> "Score":
        """Общая оценка из нескольких (например, по видам чая): средняя по отзывам, а не средняя средних."""
        mass = sum(s.mass for s in scores)
        weighted = any(s.weight_sum is not None for s in scores)
        return cls(
            avg=sum(s.avg * s.mass for s in scores) / mass if mass else 0.0,
            reviews=sum(s.reviews for s in scores),
            weight_sum=mass if weighted else None,
        )


EMPTY_SCORE = Score()


class ReviewWeighting:
    """Как отзыв учитывается в оценках чая и магазина: вес по опыту автора и поправка на его щедрость."""

    #: Вес отзыва автора, оценившего один чай. Не ноль: на старте новички все, и рейтинг не должен пустеть.
    NEWCOMER_WEIGHT = 0.2
    #: С этого числа разных оценённых чаёв отзыв весит полностью; до него вес растёт линейно.
    EXPERIENCED_TEAS = 10
    #: Насколько верить средней автора: при n отзывах его щедрость учитывается с долей n / (n + BIAS_PRIOR).
    #: Один отзыв — ещё не привычка, поэтому одиночную пятёрку почти не трогаем.
    BIAS_PRIOR = 3

    @classmethod
    def reviews(cls):
        """Подзапрос: отзывы с весом (w) и оценкой за вычетом щедрости автора (adjusted)."""
        site_mean = select(func.avg(Review.rating)).scalar_subquery()
        authors = (
            select(
                Review.user_id,
                func.count(distinct(Review.tea_id)).label("teas"),
                func.count(Review.id).label("n"),
                func.avg(Review.rating).label("mean"),
            )
            .group_by(Review.user_id)
            .subquery()
        )
        progress = func.least(func.greatest(authors.c.teas - 1, 0), cls.EXPERIENCED_TEAS - 1) / literal(
            float(cls.EXPERIENCED_TEAS - 1)
        )
        weight = cls.NEWCOMER_WEIGHT + (1 - cls.NEWCOMER_WEIGHT) * progress
        generosity = (authors.c.mean - site_mean) * authors.c.n / (authors.c.n + literal(float(cls.BIAS_PRIOR)))
        adjusted = func.least(func.greatest(Review.rating - generosity, 1), 5)
        return (
            select(
                Review.id,
                Review.tea_id,
                Review.shop_id,
                weight.label("w"),
                adjusted.label("adjusted"),
            )
            .join(authors, authors.c.user_id == Review.user_id)
            .subquery()
        )


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
        if tea_ids is not None and not tea_ids:
            return {}
        r = ReviewWeighting.reviews()
        query = select(r.c.tea_id, *_weighted_avg(r)).group_by(r.c.tea_id)
        if tea_ids is not None:
            query = query.where(r.c.tea_id.in_(tea_ids))
        rows = await self.db.execute(query)
        return {tea_id: Score.of(avg, n, w) for tea_id, n, w, avg in rows}

    async def for_offers(
        self, *, tea_ids: list[int] | None = None, category_id: int | None = None
    ) -> dict[tuple[int, int], Score]:
        """Оценки чаёв в конкретных магазинах: (tea_id, shop_id) → Score. Без отзывов — нет в словаре."""
        if tea_ids is not None and not tea_ids:
            return {}
        r = ReviewWeighting.reviews()
        query = select(r.c.tea_id, r.c.shop_id, *_weighted_avg(r)).group_by(r.c.tea_id, r.c.shop_id)
        if tea_ids is not None:
            query = query.where(r.c.tea_id.in_(tea_ids))
        if category_id is not None:
            query = query.join(Tea, Tea.id == r.c.tea_id).where(Tea.category_id == category_id)
        rows = await self.db.execute(query)
        return {(tea_id, shop_id): Score.of(avg, n, w) for tea_id, shop_id, n, w, avg in rows}

    async def by_shop_and_category(
        self, *, shop_id: int | None = None, category_id: int | None = None
    ) -> list[ShopCategoryScore]:
        """Оценки «магазин × вид чая». Виды, где у магазина есть чаи без отзывов, тоже попадают (с нулём)."""
        r = ReviewWeighting.reviews()
        query = (
            select(
                Offer.shop_id,
                Tea.category_id,
                func.count(distinct(Offer.tea_id)),
                *_weighted_avg(r),
            )
            .join(Tea, Tea.id == Offer.tea_id)
            .outerjoin(r, (r.c.tea_id == Offer.tea_id) & (r.c.shop_id == Offer.shop_id))
            .group_by(Offer.shop_id, Tea.category_id)
        )
        if shop_id is not None:
            query = query.where(Offer.shop_id == shop_id)
        if category_id is not None:
            query = query.where(Tea.category_id == category_id)
        rows = await self.db.execute(query)
        return [
            ShopCategoryScore(shop_id=s, category_id=c, score=Score.of(avg, n, w), teas=teas)
            for s, c, teas, n, w, avg in rows
        ]

    async def by_shop(self) -> dict[int, ShopScore]:
        """Общая оценка каждого магазина, у которого есть хоть один чай."""
        r = ReviewWeighting.reviews()
        query = (
            select(Offer.shop_id, func.count(distinct(Offer.tea_id)), *_weighted_avg(r))
            .outerjoin(r, (r.c.tea_id == Offer.tea_id) & (r.c.shop_id == Offer.shop_id))
            .group_by(Offer.shop_id)
        )
        rows = await self.db.execute(query)
        return {shop_id: ShopScore(score=Score.of(avg, n, w), teas=teas) for shop_id, teas, n, w, avg in rows}


def _weighted_avg(r):
    """Колонки агрегата по ReviewWeighting.reviews(): число отзывов, сумма весов, взвешенная средняя."""
    weight_sum = func.coalesce(func.sum(r.c.w), 0)
    return (
        func.count(r.c.id),
        weight_sum,
        func.sum(r.c.w * r.c.adjusted) / func.nullif(func.sum(r.c.w), 0),
    )


def best_first[T](items: list[T], score_of) -> list[T]:
    """Сортировка по сглаженной оценке, лучшие первыми."""
    return sorted(items, key=lambda item: score_of(item).weighted, reverse=True)
