"""Каталог: виды чая, магазины, чаи и предложения магазинов.

Tea — это сорт («Габа Алишань»), он не принадлежит магазину. Одну и ту же габу продают
несколько магазинов — у каждого своё предложение (Offer): «этот магазин продаёт этот чай».
Отзыв пишут на чай, купленный в конкретном магазине, то есть на предложение:
так считается и рейтинг чая (по всем магазинам), и рейтинг магазина.

Цена и партия меняются, поэтому живут в отзывах — это сведения о конкретной покупке.
Текущая цена предложения — из последнего отзыва с ценой, а пока таких нет — стартовая,
указанная при добавлении магазина (Offer.price; подзапрос к отзывам — в models/review.py).
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from back.core.db import Base
from back.core.shop_url import shop_key
from back.enums.tea_kind import TeaKind

if TYPE_CHECKING:
    from back.models.diary import DiaryEntry
    from back.models.review import Review


class Category(Base):
    """Вид чая: зелёный, улун, габа, шу пуэр…

    В таблице только сам вид. Склонения, цвета и адрес выводятся из него — см. TeaKind.
    Порядок вывода не хранится: он свой у каждой страницы (tea_kind.DEFAULT_ORDER и т.п.).
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[TeaKind] = mapped_column(SAEnum(TeaKind, name="tea_kind"), unique=True)
    teas: Mapped[list["Tea"]] = relationship(back_populates="category", lazy="raise")


class Shop(Base):
    """Магазин, который продаёт чаи."""

    __tablename__ = "shops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, comment="Системное название")
    title: Mapped[str] = mapped_column(String(128), comment="Человекочитаемое название")
    country: Mapped[str] = mapped_column(String(64))
    city: Mapped[str] = mapped_column(String(64))
    site: Mapped[str] = mapped_column(String(512))
    #: Нормализованный сайт («shop.ru», «vk.com/teashop») — уникален: один магазин не заведут дважды.
    #: Заполняется сам при записи site (см. _fill_site_key).
    site_key: Mapped[str] = mapped_column(String(255), unique=True)
    #: Кто добавил магазин (None — из сида).
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    founded_year: Mapped[int | None] = mapped_column(SmallInteger, comment="Дата основания")
    description: Mapped[str | None] = mapped_column(Text)
    #: Логотип в хранилище (back.core.storage), WebP до 256 px. None — показываем первую букву названия.
    logo_key: Mapped[str | None] = mapped_column(String(255))
    offers: Mapped[list["Offer"]] = relationship(
        back_populates="shop", lazy="raise", cascade="all, delete-orphan", passive_deletes=True
    )

    @validates("site")
    def _fill_site_key(self, _key: str, site: str) -> str:
        self.site_key = shop_key(site)
        return site


class Tea(Base):
    """Чай как сорт. Где и почём его купить — в offers."""

    __tablename__ = "teas"
    __table_args__ = (
        # «Габа Алишань» и «габа алишань» в одном виде — один и тот же чай
        Index("uq_teas_category_title", "category_id", text("lower(title)"), unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, comment="Системное название")
    title: Mapped[str] = mapped_column(String(128))
    region: Mapped[str | None] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    #: Фото чая в хранилище: большое и превью для карточек. None — рисуем чашку цвета вида.
    image_key: Mapped[str | None] = mapped_column(String(255))
    image_thumb_key: Mapped[str | None] = mapped_column(String(255))

    # Вид и предложения нужны почти всегда, когда показываем чай, — грузим сразу
    category: Mapped[Category] = relationship(back_populates="teas", lazy="joined")
    offers: Mapped[list["Offer"]] = relationship(
        back_populates="tea", lazy="selectin", cascade="all, delete-orphan", order_by="Offer.id"
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="tea", lazy="raise", cascade="all, delete-orphan", passive_deletes=True
    )
    diary_entries: Mapped[list["DiaryEntry"]] = relationship(
        back_populates="tea", lazy="raise", cascade="all, delete-orphan", passive_deletes=True
    )

    def add_offer(self, shop: Shop, **fields) -> "Offer":
        """Этот чай продаётся ещё и в магазине shop."""
        return Offer(tea=self, shop=shop, **fields)


class Offer(Base):
    """Чай в конкретном магазине. Цена — из отзывов (см. price), партия — только в отзывах."""

    __tablename__ = "offers"
    __table_args__ = (
        UniqueConstraint("tea_id", "shop_id", name="uq_offers_tea_shop"),
        CheckConstraint("(start_price IS NULL) = (start_weight IS NULL)", name="ck_offers_start_price_weight"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tea_id: Mapped[int] = mapped_column(ForeignKey("teas.id", ondelete="CASCADE"), index=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    start_price: Mapped[int | None] = mapped_column(
        Integer, comment="Цена при добавлении магазина, ₽ за start_weight г"
    )
    start_weight: Mapped[int | None] = mapped_column(SmallInteger, comment="Вес в граммах для start_price")
    url: Mapped[str | None] = mapped_column(String(512), comment="Страница чая на сайте магазина")
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tea: Mapped[Tea] = relationship(back_populates="offers", lazy="raise")
    shop: Mapped[Shop] = relationship(back_populates="offers", lazy="joined")

    # review_price / review_weight / review_price_at — цена из последнего отзыва с ценой.
    # Это column_property с подзапросом к reviews, объявлены в models/review.py.

    @property
    def price(self) -> int | None:
        """Текущая цена, ₽ за weight граммов: из последнего отзыва с ценой, иначе стартовая."""
        return self.review_price if self.review_price is not None else self.start_price

    @property
    def weight(self) -> int | None:
        return self.review_weight if self.review_price is not None else self.start_weight

    @property
    def price_at(self) -> datetime | None:
        """Когда цена была актуальна: дата отзыва или дата добавления магазина."""
        if self.review_price is not None:
            return self.review_price_at
        return self.created_at if self.start_price is not None else None

    @property
    def price_source(self) -> Literal["review", "offer"] | None:
        if self.review_price is not None:
            return "review"
        return "offer" if self.start_price is not None else None

    @property
    def price_per_gram(self) -> float | None:
        """Для сравнения магазинов: 1 250 ₽ / 50 г дороже, чем 2 000 ₽ / 100 г."""
        return self.price / self.weight if self.price is not None and self.weight else None

    @property
    def price_label(self) -> str | None:
        """Подпись цены для фронта: «1 450 ₽ / 50 г»."""
        return price_label(self.price, self.weight)


def price_label(price: int | None, weight: int | None) -> str | None:
    """«1 450 ₽ / 50 г» или None, если цены нет."""
    if price is None or not weight:
        return None
    return f"{price:,} ₽ / {weight} г".replace(",", " ")
