"""«Как заваривают этот чай»: сводка по записям дневников всех пользователей (обезличенно — только цифры).

Пока записей мало, показываем типичные параметры для вида чая — они прописаны здесь.
Граммы сравниваем на 100 мл: 5 г в гайвани на 100 мл и в чайнике на 300 мл — разная крепость.
"""

from dataclasses import dataclass
from statistics import median

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from back.enums.tea_kind import TeaKind
from back.models import DiaryEntry, Tea

#: Сводка по дневникам появляется, когда записей и людей не меньше этого.
MIN_ENTRIES = 3
MIN_PEOPLE = 2
#: «Понравилось» — оценка в записи не ниже.
LIKED_RATING = 4


@dataclass(frozen=True, slots=True)
class Typical:
    """Типичные параметры вида чая: диапазоны «от–до»."""

    water: tuple[int, int]
    grams_per_100: tuple[float, float]
    infusions: tuple[int, int]


TYPICAL: dict[TeaKind, Typical] = {
    TeaKind.GREEN: Typical((75, 80), (3, 4), (3, 4)),
    TeaKind.WHITE: Typical((85, 90), (4, 5), (5, 6)),
    TeaKind.OOLONG: Typical((90, 95), (6, 7), (7, 8)),
    TeaKind.GABA: Typical((90, 95), (5, 6), (6, 7)),
    TeaKind.RED: Typical((90, 95), (4, 5), (5, 6)),
    TeaKind.SHU: Typical((95, 100), (6, 7), (8, 10)),
    TeaKind.SHENG: Typical((90, 95), (6, 7), (8, 10)),
    TeaKind.HERBAL: Typical((95, 100), (3, 4), (2, 3)),
}
assert set(TYPICAL) == set(TeaKind), "У каждого вида чая должны быть типичные параметры"


@dataclass(frozen=True, slots=True)
class Brewed:
    """Медианы по записям дневников."""

    entries: int
    people: int
    water: int
    grams: float
    infusions: int
    #: Только по записям, где указан объём; None — объём никто не указал.
    volume: int | None
    grams_per_100: float | None


@dataclass(frozen=True, slots=True)
class Brewing:
    kind: TeaKind
    typical: Typical
    #: Как заваривают все — None, пока записей меньше MIN_ENTRIES или людей меньше MIN_PEOPLE.
    community: Brewed | None
    #: Как заваривают те, кому понравилось (оценка ≥ LIKED_RATING), — при тех же порогах по записям.
    liked: Brewed | None


def _brewed(entries: list[DiaryEntry]) -> Brewed | None:
    people = len({e.user_id for e in entries})
    if len(entries) < MIN_ENTRIES or people < MIN_PEOPLE:
        return None
    with_volume = [e for e in entries if e.volume]
    return Brewed(
        entries=len(entries),
        people=people,
        water=round(median(e.water for e in entries)),
        grams=round(float(median(e.grams for e in entries)), 1),
        infusions=round(median(e.infusions for e in entries)),
        volume=round(median(e.volume for e in with_volume)) if with_volume else None,
        grams_per_100=round(median(float(e.grams) / e.volume * 100 for e in with_volume), 1) if with_volume else None,
    )


class BrewingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def for_tea(self, tea: Tea) -> Brewing:
        entries = list(await self.db.scalars(select(DiaryEntry).where(DiaryEntry.tea_id == tea.id)))
        kind = tea.category.name
        return Brewing(
            kind=kind,
            typical=TYPICAL[kind],
            community=_brewed(entries),
            liked=_brewed([e for e in entries if e.rating >= LIKED_RATING]),
        )
