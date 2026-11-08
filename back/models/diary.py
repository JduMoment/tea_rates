from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from back.core.db import Base

if TYPE_CHECKING:
    from back.models.catalog import Shop, Tea
    from back.models.user import User


class DiaryEntry(Base):
    """Запись в личном чайном дневнике: какой чай, где куплен, как заваривал и как понравилось."""

    __tablename__ = "diary_entries"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_diary_entries_rating"),
        ForeignKeyConstraint(
            ["tea_id", "shop_id"], ["offers.tea_id", "offers.shop_id"], ondelete="CASCADE", name="fk_diary_offer"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    tea_id: Mapped[int] = mapped_column(ForeignKey("teas.id", ondelete="CASCADE"), index=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    #: День чаепития (может отличаться от дня, когда сделана запись).
    date: Mapped[date] = mapped_column(Date)
    rating: Mapped[int] = mapped_column(SmallInteger)
    water: Mapped[int] = mapped_column(SmallInteger)  # °C
    grams: Mapped[Decimal] = mapped_column(Numeric(4, 1))
    #: Объём посуды, мл. Без него граммы не сравнить: 5 г на гайвань 100 мл и на чайник 300 мл — разное.
    volume: Mapped[int | None] = mapped_column(SmallInteger)
    infusions: Mapped[int] = mapped_column(SmallInteger)
    text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="diary_entries", lazy="raise")
    # В дневнике всегда показываем, что за чай и откуда, — грузим сразу
    tea: Mapped["Tea"] = relationship(back_populates="diary_entries", lazy="joined")
    shop: Mapped["Shop"] = relationship(lazy="joined")
