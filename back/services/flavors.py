"""Вкусовой профиль чая: как часто в отзывах звучит каждый дескриптор, группа и вкус.

Доля — какая часть отзывов упомянула дескриптор. Для группы и вкуса — какая часть отзывов
упомянула хотя бы один их дескриптор (а не сумма долей: иначе выходило бы больше 100%).
Отзывы без дескрипторов в знаменатель не входят — они ничего не говорят о вкусе.
"""

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from back.enums.flavor import Flavor, FlavorGroup, Taste
from back.models import Review


@dataclass(frozen=True, slots=True)
class Share[T]:
    item: T
    #: Сколько отзывов упомянули.
    count: int
    #: count / FlavorProfile.reviews, от 0 до 1.
    share: float


@dataclass(frozen=True, slots=True)
class FlavorProfile:
    #: Отзывов, где отмечен хоть один дескриптор.
    reviews: int
    #: Только упомянутые, чаще упоминаемые первыми; в порядке колеса при равенстве.
    flavors: list[Share[Flavor]]
    groups: list[Share[FlavorGroup]]
    tastes: list[Share[Taste]]

    @classmethod
    def of(cls, picks: list[list[Flavor]]) -> "FlavorProfile":
        """Профиль из списков дескрипторов отдельных отзывов."""
        picks = [p for p in picks if p]
        flavors: Counter[Flavor] = Counter()
        groups: Counter[FlavorGroup] = Counter()
        tastes: Counter[Taste] = Counter()
        for p in picks:
            flavors.update(set(p))
            groups.update({f.group for f in p})
            tastes.update({f.taste for f in p})
        total = len(picks)
        return cls(
            reviews=total,
            flavors=_shares(flavors, list(Flavor), total),
            groups=_shares(groups, list(FlavorGroup), total),
            tastes=_shares(tastes, list(Taste), total),
        )


EMPTY_PROFILE = FlavorProfile(reviews=0, flavors=[], groups=[], tastes=[])

#: Дескрипторы отдельных отзывов: [[HONEY, PEACH], [HONEY]] — из них строится профиль.
Picks = list[list[Flavor]]


@dataclass(frozen=True, slots=True)
class FlavorMatch:
    """Насколько чай подходит под выбранные в поиске ноты."""

    #: Какие из выбранных нот слышат в чае — чаще упоминаемые первыми.
    flavors: list[Flavor]
    #: Доля отзывов (с нотами), где есть хоть одна из выбранных.
    share: float


def match_notes(picks: Picks, selected: set[Flavor]) -> FlavorMatch | None:
    """None — о вкусе чая не писали; FlavorMatch с пустым flavors — писали, но не про это."""
    picks = [p for p in picks if p]
    if not picks:
        return None
    counts = Counter(f for p in picks for f in set(p) & selected)
    hits = sum(1 for p in picks if selected.intersection(p))
    position = {f: i for i, f in enumerate(Flavor)}
    ranked = sorted(counts, key=lambda f: (-counts[f], position[f]))
    return FlavorMatch(flavors=ranked, share=hits / len(picks))


def _shares[T](counts: Counter[T], order: list[T], total: int) -> list[Share[T]]:
    position = {item: i for i, item in enumerate(order)}
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], position[kv[0]]))
    return [Share(item=item, count=n, share=n / total) for item, n in ranked]


class FlavorStatsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def picks_by_tea(self, tea_ids: Iterable[int] | None = None) -> dict[int, Picks]:
        """Дескрипторы отзывов по чаям; чаи без отзывов с нотами в словарь не попадают."""
        query = select(Review.tea_id, Review.flavors).where(func.cardinality(Review.flavors) > 0)
        if tea_ids is not None:
            query = query.where(Review.tea_id.in_(list(tea_ids)))
        picks: dict[int, Picks] = defaultdict(list)
        for tea_id, flavors in await self.db.execute(query):
            picks[tea_id].append(flavors)
        return picks

    async def for_user(self, user_id: int) -> FlavorProfile:
        """Что пользователь слышит в чаях — по его собственным отзывам."""
        query = select(Review.flavors).where(Review.user_id == user_id, func.cardinality(Review.flavors) > 0)
        return FlavorProfile.of(list(await self.db.scalars(query)))

    async def for_tea(self, tea_id: int, shop_id: int | None = None) -> FlavorProfile:
        """Профиль чая по отзывам из всех магазинов или только из shop_id."""
        query = select(Review.flavors).where(Review.tea_id == tea_id, func.cardinality(Review.flavors) > 0)
        if shop_id is not None:
            query = query.where(Review.shop_id == shop_id)
        return FlavorProfile.of(list(await self.db.scalars(query)))
