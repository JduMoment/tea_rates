from datetime import date

from pydantic import field_validator

from back.enums.shelf import ShelfStatus
from back.schemas.base import ApiModel
from back.schemas.catalog import TeaOut
from back.services.shelf import Shelved
from back.services.social import AuthorProfile


class AuthorOut(ApiModel):
    """Публичный профиль автора отзывов (без почты и дневника)."""

    id: int
    name: str
    joined: date
    reviews: int
    teas: int
    followers: int
    following: int
    followed_by_me: bool

    @classmethod
    def of(cls, p: AuthorProfile) -> "AuthorOut":
        return cls(
            id=p.user.id,
            name=p.user.name,
            joined=p.user.created_at.date(),
            reviews=p.reviews,
            teas=p.teas,
            followers=p.followers,
            following=p.following,
            followed_by_me=p.followed_by_me,
        )


class UserBriefOut(ApiModel):
    id: int
    name: str


class FollowIn(ApiModel):
    follow: bool


class ShelfItemOut(ApiModel):
    #: want / have / finished
    status: str
    #: «Хочу попробовать»
    status_label: str
    updated_at: date
    tea: TeaOut

    @classmethod
    def of(cls, s: Shelved) -> "ShelfItemOut":
        return cls(
            status=s.item.status.slug,
            status_label=s.item.status.value,
            updated_at=s.item.updated_at.date(),
            tea=TeaOut.of(s.tea),
        )


class ShelfIn(ApiModel):
    status: str

    @field_validator("status")
    @classmethod
    def check_status(cls, v: str) -> str:
        if ShelfStatus.from_slug(v) is None:
            raise ValueError("Статус — want, have или finished")
        return v

    @property
    def value(self) -> ShelfStatus:
        return ShelfStatus.from_slug(self.status)
