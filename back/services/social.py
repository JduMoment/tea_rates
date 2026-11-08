"""Публичные профили авторов, подписки и лента «новое от тех, на кого подписан»."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from back.models import Follow, Review, User
from back.services.errors import FollowSelfError, UserNotFoundError
from back.services.reviews import ReviewService, ReviewWithTea


@dataclass(frozen=True, slots=True)
class AuthorProfile:
    user: User
    reviews: int
    #: Сколько разных чаёв оценил.
    teas: int
    followers: int
    following: int
    #: Подписан ли на автора тот, кто смотрит (False для гостей и для своей страницы).
    followed_by_me: bool


class SocialService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_user(self, user_id: int) -> User:
        user = await self.db.get(User, user_id)
        if not user:
            raise UserNotFoundError
        return user

    async def profile(self, user_id: int, viewer: User | None) -> AuthorProfile:
        user = await self.get_user(user_id)
        reviews, teas = (
            await self.db.execute(
                select(func.count(Review.id), func.count(distinct(Review.tea_id))).where(Review.user_id == user_id)
            )
        ).one()
        followers = await self.db.scalar(select(func.count()).where(Follow.followee_id == user_id))
        following = await self.db.scalar(select(func.count()).where(Follow.follower_id == user_id))
        followed = bool(viewer) and await self.db.get(Follow, (viewer.id, user_id)) is not None
        return AuthorProfile(user, reviews, teas, followers or 0, following or 0, followed)

    async def follow(self, viewer: User, user_id: int, on: bool) -> AuthorProfile:
        await self.get_user(user_id)
        if viewer.id == user_id:
            raise FollowSelfError
        follow = await self.db.get(Follow, (viewer.id, user_id))
        if on and not follow:
            self.db.add(Follow(follower_id=viewer.id, followee_id=user_id))
        elif not on and follow:
            await self.db.delete(follow)
        await self.db.commit()
        return await self.profile(user_id, viewer)

    async def following(self, viewer: User) -> list[tuple[User, datetime]]:
        rows = await self.db.execute(
            select(User, Follow.created_at)
            .join(Follow, Follow.followee_id == User.id)
            .where(Follow.follower_id == viewer.id)
            .order_by(Follow.created_at.desc())
        )
        return [(u, at) for u, at in rows]

    async def feed(self, viewer: User, limit: int) -> list[ReviewWithTea]:
        followees = select(Follow.followee_id).where(Follow.follower_id == viewer.id)
        query = select(Review).where(Review.user_id.in_(followees)).order_by(Review.created_at.desc()).limit(limit)
        return await ReviewService(self.db).with_teas(query)
