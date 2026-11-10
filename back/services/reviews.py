"""Отзывы: лента свежих, отзывы пользователя, написать/удалить свой."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from back.enums.flavor import Flavor, Taste
from back.models import Review, ReviewVote, User
from back.models.review import Infusion, Purchase
from back.services.catalog import CatalogService, RatedTea
from back.services.errors import OwnReviewVoteError, ReviewNotFoundError
from back.services.experience import ExperienceRepository, ReviewerExperience
from back.services.photos import remove_files


@dataclass(frozen=True, slots=True)
class ReviewWithTea:
    """Отзыв вместе с оценённым чаем — для лент, где чай не известен из контекста."""

    review: Review
    tea: RatedTea


class ReviewService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.catalog = CatalogService(db)

    async def recent(self, limit: int) -> list[ReviewWithTea]:
        return await self.with_teas(select(Review).order_by(Review.created_at.desc()).limit(limit))

    async def by_user(self, user_id: int) -> list[ReviewWithTea]:
        return await self.with_teas(select(Review).where(Review.user_id == user_id).order_by(Review.created_at.desc()))

    async def save(
        self,
        user: User,
        tea_id: int,
        shop_id: int,
        *,
        rating: int,
        text: str,
        flavors: list[Flavor],
        purchase: Purchase,
        infusion: Infusion,
        tastes: list[Taste] = (),
    ) -> Review:
        """Пишет отзыв на чай из магазина shop_id. Если пользователь уже оценивал этот чай
        из этого магазина — заменяет прежний отзыв. Отзывы на тот же чай из других магазинов не трогает."""
        offer = await self.catalog.get_offer(tea_id, shop_id)
        review = await self.db.scalar(
            select(Review).where(Review.tea_id == tea_id, Review.shop_id == shop_id, Review.user_id == user.id)
        )
        if review:
            review.rewrite(rating, text, flavors, purchase, infusion, tastes)
        else:
            review = user.write_review(offer, rating, text, flavors, purchase, infusion, tastes)
            self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def edit(
        self,
        user: User,
        review_id: int,
        *,
        rating: int,
        text: str,
        flavors: list[Flavor],
        purchase: Purchase,
        infusion: Infusion,
        tastes: list[Taste] = (),
    ) -> Review:
        """Автор правит свой отзыв. Магазин не меняется: отзыв — о покупке в конкретном магазине."""
        review = await self.db.get(Review, review_id)
        if not review or not user.owns(review):
            raise ReviewNotFoundError
        review.edit(rating, text, flavors, purchase, infusion, tastes)
        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def delete(self, user: User, review_id: int) -> None:
        review = await self.db.get(Review, review_id)
        # Чужой отзыв для пользователя «не существует» — не подсказываем, что такой id есть
        if not review or not user.owns(review):
            raise ReviewNotFoundError
        photos = list(review.photos)
        await self.db.delete(review)
        await self.db.commit()
        remove_files(photos)

    async def get(self, review_id: int) -> Review:
        review = await self.db.get(Review, review_id)
        if not review:
            raise ReviewNotFoundError
        return review

    async def vote(self, user: User, review_id: int, helpful: bool) -> Review:
        """Отметить отзыв полезным (или снять отметку). За свой отзыв голосовать нельзя."""
        review = await self.get(review_id)
        if user.owns(review):
            raise OwnReviewVoteError
        vote = await self.db.get(ReviewVote, (review_id, user.id))
        if helpful and not vote:
            self.db.add(ReviewVote(review_id=review_id, user_id=user.id))
        elif not helpful and vote:
            await self.db.delete(vote)
        await self.db.commit()
        await self.db.refresh(review)  # пересчитать helpful
        return review

    async def voted(self, user: User | None, review_ids: list[int]) -> set[int]:
        """Какие из отзывов пользователь отметил полезными."""
        if not user or not review_ids:
            return set()
        query = select(ReviewVote.review_id).where(ReviewVote.user_id == user.id, ReviewVote.review_id.in_(review_ids))
        return set(await self.db.scalars(query))

    async def experience(self, review_ids: list[int]) -> dict[int, ReviewerExperience]:
        """Опыт авторов отзывов — для строки под именем."""
        return await ExperienceRepository(self.db).for_reviews(review_ids)

    async def with_teas(self, query) -> list[ReviewWithTea]:
        reviews = list(await self.db.scalars(query.options(selectinload(Review.tea))))
        rated = {r.tea.id: r for r in await self.catalog.rate(list({rv.tea.id: rv.tea for rv in reviews}.values()))}
        return [ReviewWithTea(review=rv, tea=rated[rv.tea_id]) for rv in reviews]
