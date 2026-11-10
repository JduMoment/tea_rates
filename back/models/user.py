from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from back.core.db import Base
from back.enums.shelf import ShelfStatus

if TYPE_CHECKING:
    from back.enums.flavor import Flavor, Taste
    from back.models.catalog import Offer, Shop, Tea
    from back.models.diary import DiaryEntry
    from back.models.review import Infusion, Purchase, Review


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    #: Хранится в нижнем регистре — уникальность без учёта регистра.
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reviews: Mapped[list["Review"]] = relationship(back_populates="user", lazy="raise", cascade="all, delete-orphan")
    diary_entries: Mapped[list["DiaryEntry"]] = relationship(
        back_populates="user", lazy="raise", cascade="all, delete-orphan"
    )

    def write_review(
        self,
        offer: "Offer",
        rating: int,
        text: str,
        flavors: list["Flavor"],
        purchase: "Purchase",
        infusion: "Infusion | None" = None,
        tastes: "list[Taste]" = (),
    ) -> "Review":
        """Новый отзыв этого пользователя на чай, купленный в магазине offer.shop."""
        from back.models.review import Infusion, Review

        review = Review(
            user=self,
            tea_id=offer.tea_id,
            shop_id=offer.shop_id,
            rating=rating,
            text=text,
            flavors=flavors,
            tastes=list(tastes),
        )
        review.set_purchase(purchase)
        review.set_infusion(infusion or Infusion())
        return review

    def add_diary_entry(self, offer: "Offer", **fields) -> "DiaryEntry":
        """Новая запись в дневнике этого пользователя."""
        from back.models.diary import DiaryEntry

        return DiaryEntry(user=self, tea_id=offer.tea_id, shop_id=offer.shop_id, **fields)

    def owns(self, obj: "Review | DiaryEntry") -> bool:
        """Принадлежит ли отзыв или запись дневника этому пользователю."""
        return obj.user_id == self.id

    def created(self, obj: "Tea | Offer | Shop") -> bool:
        """Этот ли пользователь добавил чай, предложение или магазин."""
        return obj.author_id == self.id


class UserSession(Base):
    """Серверная сессия. В cookie лежит случайный токен, в БД — только его SHA-256."""

    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    user: Mapped[User] = relationship(back_populates="sessions", lazy="joined")


class UserIdentity(Base):
    """Привязка аккаунта внешнего провайдера (пока только Яндекс) к пользователю.

    Ищем по (provider, subject) — постоянному id у провайдера, а не по почте:
    почту в Яндексе можно сменить, id — нет.
    """

    __tablename__ = "user_identities"
    __table_args__ = (UniqueConstraint("provider", "subject"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(16))
    subject: Mapped[str] = mapped_column(String(128))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(lazy="joined")


class ShelfItem(Base):
    """«Мои чаи»: чай в личном шкафу пользователя со статусом — хочу попробовать, есть дома, закончился."""

    __tablename__ = "shelf_items"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    tea_id: Mapped[int] = mapped_column(ForeignKey("teas.id", ondelete="CASCADE"), primary_key=True, index=True)
    status: Mapped[ShelfStatus] = mapped_column(SAEnum(ShelfStatus, name="shelf_status"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Follow(Base):
    """Подписка: follower читает отзывы followee в своей ленте."""

    __tablename__ = "follows"
    __table_args__ = (CheckConstraint("follower_id <> followee_id", name="ck_follows_not_self"),)

    follower_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    followee_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PasswordReset(Base):
    """Ссылка для сброса пароля. В письме — случайный токен, здесь — только его SHA-256."""

    __tablename__ = "password_resets"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
