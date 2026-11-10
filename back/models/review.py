from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from back.core.db import Base
from back.enums.flavor import Flavor, Taste
from back.enums.season import Season
from back.models.catalog import Offer, price_label

if TYPE_CHECKING:
    from back.models.catalog import Shop, Tea
    from back.models.user import User

#: Дескрипторы в БД — массив строк с именами членов Flavor (HONEY). Не нативный enum Postgres:
#: дескрипторы будут добавляться, а ALTER TYPE ... ADD VALUE неудобен.
FlavorArray = ARRAY(SAEnum(Flavor, native_enum=False, length=32, validate_strings=True))
#: Базовые вкусы, которые автор отметил сам (SWEET, UMAMI) — так же строками.
TasteArray = ARRAY(SAEnum(Taste, native_enum=False, length=16, validate_strings=True))


class Review(Base):
    """Отзыв пользователя на чай, купленный в конкретном магазине.

    Один пользователь — один отзыв на пару «чай × магазин»: одну габу из трёх магазинов
    можно оценить трижды. Пара обязана существовать в offers — отзыв только на то, что продаётся.
    """

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("tea_id", "shop_id", "user_id", name="uq_reviews_tea_shop_user"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating"),
        CheckConstraint("(price IS NULL) = (weight IS NULL)", name="ck_reviews_price_weight"),
        CheckConstraint("body BETWEEN 1 AND 5", name="ck_reviews_body"),
        CheckConstraint("strength BETWEEN 1 AND 5", name="ck_reviews_strength"),
        CheckConstraint("aftertaste BETWEEN 1 AND 5", name="ck_reviews_aftertaste"),
        CheckConstraint("astringency BETWEEN 1 AND 5", name="ck_reviews_astringency"),
        ForeignKeyConstraint(
            ["tea_id", "shop_id"], ["offers.tea_id", "offers.shop_id"], ondelete="CASCADE", name="fk_reviews_offer"
        ),
        Index("ix_reviews_flavors", "flavors", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tea_id: Mapped[int] = mapped_column(ForeignKey("teas.id", ondelete="CASCADE"), index=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column(SmallInteger)
    text: Mapped[str] = mapped_column(Text)
    #: Дескрипторы, которые услышал автор. Группа и вкус выводятся из них (Flavor.group / .taste).
    flavors: Mapped[list[Flavor]] = mapped_column(FlavorArray, default=list)
    #: Вкус, отмеченный автором. Пусто — не отмечал (или отзыв старше этого поля): тогда вкус выводится из нот.
    tastes: Mapped[list[Taste]] = mapped_column(TasteArray, default=list, server_default="{}")
    # Покупка: сколько заплатил и какую партию взял. Необязательно; цена — вместе с весом.
    price: Mapped[int | None] = mapped_column(Integer, comment="Цена покупки, ₽ за weight граммов")
    weight: Mapped[int | None] = mapped_column(SmallInteger, comment="Вес в граммах для price")
    harvest_year: Mapped[int | None] = mapped_column(SmallInteger, comment="Год сбора купленной партии")
    harvest_season: Mapped[Season | None] = mapped_column(SAEnum(Season, name="harvest_season"), comment="Сезон сбора")
    # Настой по шкалам 1–5, всё необязательно: тело (лёгкий → плотный), насыщенность (пустой → крепкий),
    # послевкусие (быстро уходит → долгое).
    body: Mapped[int | None] = mapped_column(SmallInteger)
    strength: Mapped[int | None] = mapped_column(SmallInteger)
    aftertaste: Mapped[int | None] = mapped_column(SmallInteger)
    #: Терпкость: мягкий → вяжущий.
    astringency: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    #: Когда автор поправил отзыв («изменён»). Дата отзыва при правке не меняется. None — не правили.
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Имя автора и магазин показываем у каждого отзыва — грузим сразу
    user: Mapped["User"] = relationship(back_populates="reviews", lazy="joined")
    shop: Mapped["Shop"] = relationship(lazy="joined")
    # Чай нужен не всегда (на странице чая он и так известен) — только явно через selectinload
    tea: Mapped["Tea"] = relationship(back_populates="reviews", lazy="raise")
    photos: Mapped[list["ReviewPhoto"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="ReviewPhoto.position, ReviewPhoto.id"
    )

    @property
    def price_label(self) -> str | None:
        """«1 450 ₽ / 50 г» или None."""
        return price_label(self.price, self.weight)

    @property
    def harvest(self) -> str:
        """Подпись сбора для фронта: «Весна 2025», «2018», «Осень» или пустая строка."""
        parts = [self.harvest_season.value if self.harvest_season else None, self.harvest_year]
        return " ".join(str(p) for p in parts if p)

    @property
    def effective_tastes(self) -> set[Taste]:
        """Вкус отзыва: отмеченный автором, а если не отмечал — выведенный из нот."""
        return set(self.tastes) or {f.taste for f in self.flavors}

    def rewrite(
        self,
        rating: int,
        text: str,
        flavors: list[Flavor],
        purchase: "Purchase",
        infusion: "Infusion",
        tastes: list[Taste] = (),
    ) -> None:
        """Повторный отзыв на тот же чай из того же магазина (новая покупка) заменяет старый
        и поднимается наверх как свежий."""
        self.edit(rating, text, flavors, purchase, infusion, tastes)
        self.created_at = datetime.now(UTC)
        self.edited_at = None

    def edit(
        self,
        rating: int,
        text: str,
        flavors: list[Flavor],
        purchase: "Purchase",
        infusion: "Infusion",
        tastes: list[Taste] = (),
    ) -> None:
        """Правка отзыва автором: дата остаётся прежней (и цена в истории — на дату покупки), ставим «изменён»."""
        self.rating = rating
        self.text = text
        self.flavors = flavors
        self.tastes = list(tastes)
        self.set_purchase(purchase)
        self.set_infusion(infusion)
        self.edited_at = datetime.now(UTC)

    def set_infusion(self, infusion: "Infusion") -> None:
        self.body = infusion.body
        self.strength = infusion.strength
        self.aftertaste = infusion.aftertaste
        self.astringency = infusion.astringency

    def set_purchase(self, purchase: "Purchase") -> None:
        self.price = purchase.price
        self.weight = purchase.weight
        self.harvest_year = purchase.harvest_year
        self.harvest_season = purchase.harvest_season


@dataclass(frozen=True, slots=True)
class Purchase:
    """Что известно о покупке из отзыва. Всё необязательно; цена — только вместе с весом."""

    price: int | None = None
    weight: int | None = None
    harvest_year: int | None = None
    harvest_season: Season | None = None


@dataclass(frozen=True, slots=True)
class Infusion:
    """Настой по шкалам 1–5 (None — не оценивал)."""

    body: int | None = None
    strength: int | None = None
    aftertaste: int | None = None
    astringency: int | None = None


class ReviewVote(Base):
    """«Полезный отзыв»: один голос от пользователя, за свой отзыв голосовать нельзя."""

    __tablename__ = "review_votes"

    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReviewPhoto(Base):
    """Фото к отзыву. Файлы — в хранилище (core/storage.py), здесь только ключи и размеры."""

    __tablename__ = "review_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(SmallInteger, default=0)
    #: Ключи файлов в хранилище: большое фото и превью.
    key: Mapped[str] = mapped_column(String(128))
    thumb_key: Mapped[str] = mapped_column(String(128))
    width: Mapped[int] = mapped_column(SmallInteger)
    height: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Число голосов «полезно» — подзапросом при загрузке отзыва
Review.helpful = column_property(
    select(func.count(ReviewVote.user_id))
    .where(ReviewVote.review_id == Review.id)
    .correlate_except(ReviewVote)
    .scalar_subquery()
)


# ---------- текущая цена предложения ----------
# Цена из последнего отзыва на эту пару «чай × магазин», где цена указана. Считается подзапросом
# при загрузке Offer, поэтому всегда актуальна: и после нового отзыва, и после удаления старого.
# Объявлено здесь, а не в catalog.py, — там ещё нет класса Review.

_latest_priced = (
    select(Review.price, Review.weight, Review.created_at)
    .where(Review.tea_id == Offer.tea_id, Review.shop_id == Offer.shop_id, Review.price.is_not(None))
    .order_by(Review.created_at.desc(), Review.id.desc())
    .limit(1)
    .correlate_except(Review)
)
Offer.review_price = column_property(_latest_priced.with_only_columns(Review.price).scalar_subquery())
Offer.review_weight = column_property(_latest_priced.with_only_columns(Review.weight).scalar_subquery())
Offer.review_price_at = column_property(_latest_priced.with_only_columns(Review.created_at).scalar_subquery())
