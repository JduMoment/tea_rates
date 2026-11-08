from typing import Annotated, ClassVar

from fastapi import Query, status

from back.core.auth import CurrentUser, OptionalUser
from back.core.deps import ReviewsDep, ShelfDep, SocialDep
from back.core.views import View
from back.schemas.reviews import ReviewOut
from back.schemas.social import AuthorOut, FollowIn, ShelfIn, ShelfItemOut, UserBriefOut


class AuthorView(View):
    """Публичный профиль автора: сколько отзывов и чаёв, подписчики. Отзывы — /users/{id}/reviews,
    вкус — /users/{id}/flavors."""

    paths = ("/users/{user_id}",)

    async def get(self, user_id: int, social: SocialDep, viewer: OptionalUser) -> AuthorOut:
        return AuthorOut.of(await social.profile(user_id, viewer))


class FollowView(View):
    """Подписаться на автора (PUT {"follow": true}) или отписаться ({"follow": false})."""

    paths = ("/users/{user_id}/follow",)

    async def put(self, user_id: int, data: FollowIn, viewer: CurrentUser, social: SocialDep) -> AuthorOut:
        return AuthorOut.of(await social.follow(viewer, user_id, data.follow))


class FollowingView(View):
    """На кого подписан текущий пользователь."""

    paths = ("/me/following",)

    async def get(self, viewer: CurrentUser, social: SocialDep) -> list[UserBriefOut]:
        return [UserBriefOut(id=u.id, name=u.name) for u, _ in await social.following(viewer)]


class FeedView(View):
    """Лента: свежие отзывы тех, на кого подписан текущий пользователь."""

    paths = ("/me/feed",)

    async def get(
        self,
        viewer: CurrentUser,
        social: SocialDep,
        reviews: ReviewsDep,
        limit: Annotated[int, Query(ge=1, le=50)] = 12,
    ) -> list[ReviewOut]:
        items = await social.feed(viewer, limit)
        voted = await reviews.voted(viewer, [x.review.id for x in items])
        return [ReviewOut.of(x.review, x.tea, voted) for x in items]


class ShelfView(View):
    """«Мои чаи»: шкаф текущего пользователя, недавно изменённые первыми."""

    paths = ("/me/shelf",)

    async def get(self, user: CurrentUser, shelf: ShelfDep) -> list[ShelfItemOut]:
        return [ShelfItemOut.of(s) for s in await shelf.items(user)]


class ShelfItemView(View):
    """Положить чай в шкаф или сменить статус (PUT {"status": "want"|"have"|"finished"}), убрать — DELETE."""

    paths = ("/me/shelf/{tea_id}",)
    method_options: ClassVar[dict] = {"delete": {"status_code": status.HTTP_204_NO_CONTENT}}

    async def put(self, tea_id: int, data: ShelfIn, user: CurrentUser, shelf: ShelfDep) -> ShelfItemOut:
        return ShelfItemOut.of(await shelf.put(user, tea_id, data.value))

    async def delete(self, tea_id: int, user: CurrentUser, shelf: ShelfDep) -> None:
        await shelf.remove(user, tea_id)
