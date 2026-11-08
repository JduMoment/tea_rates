from typing import Annotated, ClassVar

from fastapi import HTTPException, Query, UploadFile, status

from back.core.auth import CurrentUser, OptionalUser
from back.core.deps import PhotosDep, ReviewsDep
from back.core.views import View
from back.schemas.reviews import ReviewIn, ReviewOut, VoteIn
from back.services.photos import MAX_BYTES, PhotoError


class RecentReviewsView(View):
    """Лента свежих отзывов."""

    paths = ("/reviews",)

    async def get(
        self, reviews: ReviewsDep, user: OptionalUser, limit: Annotated[int, Query(ge=1, le=50)] = 6
    ) -> list[ReviewOut]:
        return await _out(reviews, user, await reviews.recent(limit))


class UserReviewsView(View):
    """Все отзывы пользователя (профиль)."""

    paths = ("/users/{user_id}/reviews",)

    async def get(self, user_id: int, reviews: ReviewsDep, user: OptionalUser) -> list[ReviewOut]:
        return await _out(reviews, user, await reviews.by_user(user_id))


class TeaReviewsView(View):
    """Оставить отзыв на чай, купленный в магазине shopId. Повторный отзыв того же пользователя
    на тот же чай из того же магазина заменяет прежний."""

    paths = ("/teas/{tea_id}/reviews",)
    route_options: ClassVar[dict] = {"status_code": status.HTTP_201_CREATED}

    async def post(self, tea_id: int, data: ReviewIn, user: CurrentUser, reviews: ReviewsDep) -> ReviewOut:
        review = await reviews.save(
            user,
            tea_id,
            data.shop_id,
            rating=data.rating,
            text=data.text,
            flavors=data.flavors,
            purchase=data.purchase(),
            infusion=data.infusion(),
        )
        return ReviewOut.of(review)


class ReviewView(View):
    paths = ("/reviews/{review_id}",)
    route_options: ClassVar[dict] = {"status_code": status.HTTP_204_NO_CONTENT}

    async def delete(self, review_id: int, user: CurrentUser, reviews: ReviewsDep) -> None:
        await reviews.delete(user, review_id)


class ReviewVoteView(View):
    """«Полезный отзыв»: PUT {"helpful": true|false}. Возвращает отзыв с новым числом голосов."""

    paths = ("/reviews/{review_id}/vote",)

    async def put(self, review_id: int, data: VoteIn, user: CurrentUser, reviews: ReviewsDep) -> ReviewOut:
        review = await reviews.vote(user, review_id, data.helpful)
        return ReviewOut.of(review, voted={review.id} if data.helpful else set())


class ReviewPhotosView(View):
    """Добавить фото к своему отзыву (multipart, поле file). До 3 фото, до 10 МБ; JPEG, PNG или WebP."""

    paths = ("/reviews/{review_id}/photos",)
    route_options: ClassVar[dict] = {"status_code": status.HTTP_201_CREATED}

    async def post(self, review_id: int, file: UploadFile, user: CurrentUser, photos: PhotosDep) -> ReviewOut:
        data = await file.read(MAX_BYTES + 1)
        try:
            review = await photos.add(user, review_id, data)
        except PhotoError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from None
        return ReviewOut.of(review)


class ReviewPhotoView(View):
    paths = ("/reviews/{review_id}/photos/{photo_id}",)
    route_options: ClassVar[dict] = {"status_code": status.HTTP_204_NO_CONTENT}

    async def delete(self, review_id: int, photo_id: int, user: CurrentUser, photos: PhotosDep) -> None:
        await photos.delete(user, review_id, photo_id)


async def _out(reviews: ReviewsDep, user, items) -> list[ReviewOut]:
    voted = await reviews.voted(user, [x.review.id for x in items])
    return [ReviewOut.of(x.review, x.tea, voted) for x in items]
