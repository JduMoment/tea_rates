"""Опыт автора отзывов: сколько разных чаёв, видов чая и магазинов он оценил.

Показываем под именем в каждом отзыве («23 чая · 6 видов · 4 магазина · из них шу пуэров — 8»)
и на странице автора — чтобы читатель видел, кто пишет. Считаем по отзывам, как и вес отзыва
в оценках (scoring.ReviewWeighting). Сам вес в процентах не показываем никому.
"""

from dataclasses import dataclass

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from back.enums.tea_kind import TeaKind, in_order
from back.models import Category, Review, Tea


@dataclass(frozen=True, slots=True)
class Experience:
    teas: int
    kinds: int
    shops: int


@dataclass(frozen=True, slots=True)
class ReviewerExperience(Experience):
    """Опыт автора конкретного отзыва + сколько он оценил чаёв того же вида, что и в отзыве."""

    kind: TeaKind
    same_kind: int


@dataclass(frozen=True, slots=True)
class AuthorExperience(Experience):
    """Опыт автора для его страницы: с разбивкой по видам чая (от лёгких к плотным)."""

    by_kind: list[tuple[TeaKind, int]]


class ExperienceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def for_reviews(self, review_ids: list[int]) -> dict[int, ReviewerExperience]:
        """Опыт авторов отзывов review_ids — один запрос на всех."""
        if not review_ids:
            return {}
        authors = select(Review.user_id).where(Review.id.in_(review_ids))
        totals = (
            select(
                Review.user_id,
                func.count(distinct(Review.tea_id)).label("teas"),
                func.count(distinct(Tea.category_id)).label("kinds"),
                func.count(distinct(Review.shop_id)).label("shops"),
            )
            .join(Tea, Tea.id == Review.tea_id)
            .where(Review.user_id.in_(authors))
            .group_by(Review.user_id)
            .subquery()
        )
        per_kind = (
            select(Review.user_id, Tea.category_id, func.count(distinct(Review.tea_id)).label("n"))
            .join(Tea, Tea.id == Review.tea_id)
            .where(Review.user_id.in_(authors))
            .group_by(Review.user_id, Tea.category_id)
            .subquery()
        )
        rows = await self.db.execute(
            select(Review.id, totals.c.teas, totals.c.kinds, totals.c.shops, Category.name, per_kind.c.n)
            .join(Tea, Tea.id == Review.tea_id)
            .join(Category, Category.id == Tea.category_id)
            .join(totals, totals.c.user_id == Review.user_id)
            .join(per_kind, (per_kind.c.user_id == Review.user_id) & (per_kind.c.category_id == Tea.category_id))
            .where(Review.id.in_(review_ids))
        )
        return {
            rid: ReviewerExperience(teas=teas, kinds=kinds, shops=shops, kind=kind, same_kind=n)
            for rid, teas, kinds, shops, kind, n in rows
        }

    async def of_user(self, user_id: int) -> AuthorExperience:
        rows = (
            await self.db.execute(
                select(Category.name, func.count(distinct(Review.tea_id)))
                .join(Tea, Tea.id == Review.tea_id)
                .join(Category, Category.id == Tea.category_id)
                .where(Review.user_id == user_id)
                .group_by(Category.name)
            )
        ).all()
        teas, shops = (
            await self.db.execute(
                select(func.count(distinct(Review.tea_id)), func.count(distinct(Review.shop_id))).where(
                    Review.user_id == user_id
                )
            )
        ).one()
        by_kind = sorted(in_order([(k, n) for k, n in rows], lambda r: r[0]), key=lambda r: -r[1])
        return AuthorExperience(teas=teas, kinds=len(rows), shops=shops, by_kind=by_kind)
