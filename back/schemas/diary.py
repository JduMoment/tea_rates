from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from pydantic import field_validator

from back.schemas.base import ApiModel
from back.schemas.catalog import ShopBriefOut, TeaOut
from back.schemas.reviews import Rating
from back.services.diary import DiaryItem


class DiaryEntryIn(ApiModel):
    tea_id: int
    #: Где куплен чай.
    shop_id: int
    date: date
    rating: Rating
    water: int
    grams: Decimal
    #: Объём посуды, мл — необязательно.
    volume: int | None = None
    infusions: int
    text: str = ""

    @field_validator("date")
    @classmethod
    def check_date(cls, v: date) -> date:
        # +1 день запаса: у пользователя может быть уже «завтра» относительно UTC
        if v > datetime.now(UTC).date() + timedelta(days=1):
            raise ValueError("Дата чаепития не может быть в будущем")
        return v

    @field_validator("water")
    @classmethod
    def check_water(cls, v: int) -> int:
        if not 40 <= v <= 100:
            raise ValueError("Температура воды — от 40 до 100 °C")
        return v

    @field_validator("grams")
    @classmethod
    def check_grams(cls, v: Decimal) -> Decimal:
        if not Decimal("0.5") <= v <= Decimal(50):
            raise ValueError("Заварка — от 0,5 до 50 г")
        return v.quantize(Decimal("0.1"))

    @field_validator("volume")
    @classmethod
    def check_volume(cls, v: int | None) -> int | None:
        if v is not None and not 20 <= v <= 3000:
            raise ValueError("Объём посуды — от 20 до 3000 мл")
        return v

    @field_validator("infusions")
    @classmethod
    def check_infusions(cls, v: int) -> int:
        if not 1 <= v <= 50:
            raise ValueError("Проливов — от 1 до 50")
        return v

    @field_validator("text")
    @classmethod
    def check_text(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 4000:
            raise ValueError("Слишком длинная заметка — до 4000 символов")
        return v


class DiaryEntryOut(ApiModel):
    id: int
    user_id: int
    tea_id: int
    shop_id: int
    date: date
    rating: int
    water: int
    grams: float
    volume: int | None
    infusions: int
    text: str
    tea: TeaOut
    shop: ShopBriefOut

    @classmethod
    def of(cls, item: DiaryItem) -> "DiaryEntryOut":
        e = item.entry
        return cls(
            id=e.id,
            user_id=e.user_id,
            tea_id=e.tea_id,
            shop_id=e.shop_id,
            date=e.date,
            rating=e.rating,
            water=e.water,
            grams=float(e.grams),
            volume=e.volume,
            infusions=e.infusions,
            text=e.text,
            tea=TeaOut.of(item.tea),
            shop=ShopBriefOut.of(e.shop),
        )
