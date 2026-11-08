"""«Вам может понравиться»: чаи, вкус которых похож на то, что пользователь любит.

Вкус пользователя — ноты из его отзывов с весом по оценке: что отмечал в чаях на 5 — тянет
сильнее, в чаях на 4 — слабее, на 3 — никак, в нелюбимых — отталкивает. Вкус чая — доли
отзывов, упомянувших каждую ноту. Похожесть — косинус между ними по нотам и, с меньшим весом,
по группам: «курага» у пользователя и «изюм» у чая — разные ноты, но одна группа.
"""

import math
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from back.enums.flavor import Flavor, FlavorGroup
from back.models import Review, Tea
from back.services.catalog import CatalogService, RatedTea
from back.services.flavors import FlavorProfile, FlavorStatsService

#: Столько отзывов с нотами нужно пользователю, чтобы было с чем сравнивать.
MIN_REVIEWS = 3
#: Вклад совпадения по группам относительно совпадения по нотам.
GROUP_WEIGHT = 0.5
#: Чаи с оценкой ниже не советуем, как бы ни совпал вкус.
MIN_AVG = 3.5
#: Сколько нот показывать как причину совета.
REASONS = 3


@dataclass(frozen=True, slots=True)
class Recommendation:
    rated: RatedTea
    #: Общие ноты пользователя и чая — самые весомые первыми.
    reasons: list[Flavor]
    #: Похожесть от 0 до 1.
    score: float


@dataclass(frozen=True, slots=True)
class Recommendations:
    #: Отзывов пользователя с нотами.
    reviews: int
    #: Сколько их нужно для советов (MIN_REVIEWS).
    needed: int
    items: list[Recommendation]


def _rating_weight(rating: int) -> int:
    """5 → 2, 4 → 1, 3 → 0, 2 → −1, 1 → −2."""
    return rating - 3


def _cosine[K](a: Mapping[K, float], b: Mapping[K, float]) -> float:
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    norm = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return dot / norm if norm else 0.0


class UserTaste:
    """Вкус пользователя: вес каждой ноты и группы по его отзывам."""

    def __init__(self, reviews: Iterable[tuple[int, list[Flavor]]]) -> None:
        self.flavors: Counter[Flavor] = Counter()
        self.groups: Counter[FlavorGroup] = Counter()
        for rating, flavors in reviews:
            w = _rating_weight(rating)
            for f in set(flavors):
                self.flavors[f] += w
            for g in {f.group for f in flavors}:
                self.groups[g] += w

    @property
    def likes_something(self) -> bool:
        return any(v > 0 for v in self.flavors.values())

    def similarity(self, tea: FlavorProfile) -> tuple[float, list[Flavor]]:
        """Похожесть от 0 до 1 и общие любимые ноты."""
        tea_flavors = {s.item: s.share for s in tea.flavors}
        tea_groups = {s.item: s.share for s in tea.groups}
        raw = _cosine(self.flavors, tea_flavors) + GROUP_WEIGHT * _cosine(self.groups, tea_groups)
        # Профиль по одному-двум отзывам — случайность; доверяем ему меньше
        confidence = tea.reviews / (tea.reviews + 1)
        score = max(0.0, raw / (1 + GROUP_WEIGHT)) * confidence
        common = [f for f in tea_flavors if self.flavors[f] > 0]
        common.sort(key=lambda f: -self.flavors[f] * tea_flavors[f])
        return score, common[:REASONS]


class RecommendationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.catalog = CatalogService(db)
        self.flavors = FlavorStatsService(db)

    async def for_user(self, user_id: int, limit: int) -> Recommendations:
        mine = (
            await self.db.execute(select(Review.tea_id, Review.rating, Review.flavors).where(Review.user_id == user_id))
        ).all()
        with_notes = [(r.rating, r.flavors) for r in mine if r.flavors]
        empty = Recommendations(reviews=len(with_notes), needed=MIN_REVIEWS, items=[])
        taste = UserTaste(with_notes)
        if len(with_notes) < MIN_REVIEWS or not taste.likes_something:
            return empty

        tried = {r.tea_id for r in mine}  # чаи, на которые уже писал отзыв, — в любом магазине
        scored: list[tuple[int, float, list[Flavor]]] = []
        for tea_id, picks in (await self.flavors.picks_by_tea()).items():
            if tea_id in tried:
                continue
            score, reasons = taste.similarity(FlavorProfile.of(picks))
            if score > 0 and reasons:
                scored.append((tea_id, score, reasons))
        scored.sort(key=lambda x: -x[1])

        teas = {t.id: t for t in await self.db.scalars(select(Tea).where(Tea.id.in_([x[0] for x in scored])))}
        rated = {r.tea.id: r for r in await self.catalog.rate(list(teas.values()))}
        items = [
            Recommendation(rated=rated[tea_id], reasons=reasons, score=score)
            for tea_id, score, reasons in scored
            if rated[tea_id].score.avg >= MIN_AVG
        ]
        return Recommendations(reviews=len(with_notes), needed=MIN_REVIEWS, items=items[:limit])
