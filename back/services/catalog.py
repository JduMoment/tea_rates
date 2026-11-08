"""Каталог: виды чая, магазины, чаи и их предложения — с оценками."""

from collections import defaultdict
from dataclasses import dataclass, field, replace
from enum import StrEnum

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from back.enums.flavor import Flavor
from back.enums.tea_kind import TeaKind, in_order
from back.models import Category, Offer, Review, Shop, Tea
from back.services.errors import CategoryNotFoundError, OfferNotFoundError, ShopNotFoundError, TeaNotFoundError
from back.services.flavors import FlavorMatch, FlavorProfile, FlavorStatsService, match_notes
from back.services.scoring import EMPTY_SCORE, Score, ScoreRepository, ShopCategoryScore, best_first


@dataclass(frozen=True, slots=True)
class RatedTea:
    """Чай вместе с его оценкой (по отзывам из всех магазинов)."""

    tea: Tea
    score: Score
    #: Только при поиске по вкусу: совпадение с выбранными нотами; None — о вкусе ещё не писали.
    flavor_match: FlavorMatch | None = None


@dataclass(frozen=True, slots=True)
class RatedOffer:
    """Чай в конкретном магазине и его оценка по отзывам на покупки именно там."""

    offer: Offer
    score: Score
    #: Место магазина в рейтинге по виду этого чая (есть только на странице чая).
    shop_rank: int | None = None


@dataclass(slots=True)
class ShopSummary:
    shop: Shop
    score: Score
    tea_count: int
    #: «Фирменные» виды чая магазина — где он особенно хорош по отзывам.
    specialties: list[ShopCategoryScore] = field(default_factory=list)


@dataclass(slots=True)
class ShopDetails:
    summary: ShopSummary
    #: Оценки по всем видам чая магазина, лучшие первыми.
    scores: list[ShopCategoryScore]
    teas: list[RatedTea]


@dataclass(slots=True)
class TeaDetails:
    rated: RatedTea
    #: Где купить: магазины с оценкой этого чая у каждого, лучшие первыми.
    offers: list[RatedOffer]
    reviews: list[Review]
    #: Другие чаи того же вида.
    alternatives: list[RatedTea]
    #: Вкусовой профиль по отзывам из всех магазинов.
    flavors: FlavorProfile
    #: Средние шкалы настоя по отзывам, где их отметили.
    infusion: "InfusionStats"


@dataclass(frozen=True, slots=True)
class InfusionStats:
    """Средние по шкалам настоя (1–5) и сколько отзывов их отметили; None — никто не отметил."""

    body: float | None
    strength: float | None
    aftertaste: float | None
    reviews: int

    @classmethod
    def of(cls, reviews: list[Review]) -> "InfusionStats":
        def avg(values: list[int | None]) -> float | None:
            marked = [v for v in values if v is not None]
            return round(sum(marked) / len(marked), 1) if marked else None

        rated = [r for r in reviews if r.body or r.strength or r.aftertaste]
        return cls(
            body=avg([r.body for r in rated]),
            strength=avg([r.strength for r in rated]),
            aftertaste=avg([r.aftertaste for r in rated]),
            reviews=len(rated),
        )


class TeaSort(StrEnum):
    RATING = "rating"
    #: Дешёвые первыми — по цене за грамм в самом дешёвом магазине; чаи без цены в конце.
    PRICE = "price"
    REVIEWS = "reviews"
    TITLE = "title"


def rank_shops(scores: list[ShopCategoryScore]) -> list[ShopCategoryScore]:
    """Рейтинг магазинов внутри вида чая."""
    return best_first(scores, lambda s: s.score)


class CatalogService:
    ALTERNATIVES_LIMIT = 4

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.scores = ScoreRepository(db)

    # ---------- виды чая ----------

    async def categories(self) -> list[Category]:
        """Все виды чая в порядке по умолчанию (tea_kind.DEFAULT_ORDER)."""
        return in_order(list(await self.db.scalars(select(Category))), lambda c: c.name)

    async def category(self, slug: str) -> Category:
        """Вид чая по адресу: «gaba» → Габа. Неизвестный слаг или вид, которого нет в БД, — 404."""
        kind = TeaKind.from_slug(slug)
        category = await self.db.scalar(select(Category).where(Category.name == kind)) if kind else None
        if not category:
            raise CategoryNotFoundError
        return category

    # ---------- магазины ----------

    async def shops(self) -> list[ShopSummary]:
        shops = await self.db.scalars(select(Shop))
        totals = await self.scores.by_shop()
        specialties: dict[int, list[ShopCategoryScore]] = defaultdict(list)
        for s in rank_shops(await self.scores.by_shop_and_category()):
            if s.score.is_specialty:
                specialties[s.shop_id].append(s)
        summaries = [
            ShopSummary(
                shop=shop,
                score=totals[shop.id].score if shop.id in totals else EMPTY_SCORE,
                tea_count=totals[shop.id].teas if shop.id in totals else 0,
                specialties=specialties[shop.id],
            )
            for shop in shops
        ]
        return sorted(summaries, key=lambda s: s.score.avg, reverse=True)

    async def get_shop(self, name: str) -> Shop:
        """Магазин по техническому имени из адреса: «art-of-tea»."""
        shop = await self.db.scalar(select(Shop).where(Shop.name == name))
        if not shop:
            raise ShopNotFoundError
        return shop

    async def get_shop_by_id(self, shop_id: int) -> Shop:
        shop = await self.db.get(Shop, shop_id)
        if not shop:
            raise ShopNotFoundError
        return shop

    async def shop(self, name: str) -> ShopDetails:
        shop = await self.get_shop(name)
        scores = rank_shops(await self.scores.by_shop_and_category(shop_id=shop.id))
        teas = await self.teas(shop_id=shop.id)
        total = Score.of(
            avg=_mean([s.score for s in scores]),
            reviews=sum(s.score.reviews for s in scores),
        )
        summary = ShopSummary(
            shop=shop,
            score=total,
            tea_count=len(teas),
            specialties=[s for s in scores if s.score.is_specialty],
        )
        return ShopDetails(summary=summary, scores=scores, teas=teas)

    # ---------- чаи ----------

    async def rate(self, teas: list[Tea]) -> list[RatedTea]:
        """Прикрепляет к чаям их оценки (один запрос на всех)."""
        scores = await self.scores.for_teas([t.id for t in teas])
        return [RatedTea(tea=t, score=scores.get(t.id, EMPTY_SCORE)) for t in teas]

    async def teas(
        self,
        *,
        category_id: int | None = None,
        shop_id: int | None = None,
        q: str | None = None,
        flavors: list[Flavor] | None = None,
        sort: TeaSort = TeaSort.RATING,
    ) -> list[RatedTea]:
        """С flavors — поиск по вкусу: чаи, где слышат хоть одну из нот (больше совпадений — выше),
        за ними чаи, о вкусе которых ещё не писали. Чаи, где эти ноты не слышат, не попадают."""
        query = select(Tea)
        if category_id is not None:
            query = query.where(Tea.category_id == category_id)
        if shop_id is not None:
            query = query.where(Tea.id.in_(select(Offer.tea_id).where(Offer.shop_id == shop_id)))
        if q and (q := q.strip()):
            query = query.where(_search(q))
        rated = await self.rate(list(await self.db.scalars(query)))
        match sort:
            case TeaSort.TITLE:
                rated = sorted(rated, key=lambda r: r.tea.title.casefold())
            case TeaSort.REVIEWS:
                rated = sorted(rated, key=lambda r: r.score.reviews, reverse=True)
            case TeaSort.PRICE:
                rated = sorted(rated, key=lambda r: per_gram(r.tea) or float("inf"))
            case _:
                rated = best_first(rated, lambda r: r.score)
        return await self._by_flavor(rated, set(flavors)) if flavors else rated

    async def _by_flavor(self, rated: list[RatedTea], selected: set[Flavor]) -> list[RatedTea]:
        picks = await FlavorStatsService(self.db).picks_by_tea(r.tea.id for r in rated)
        matched: list[RatedTea] = []
        undescribed: list[RatedTea] = []
        for r in rated:
            m = match_notes(picks.get(r.tea.id, []), selected)
            if m is None:
                undescribed.append(r)
            elif m.flavors:
                matched.append(replace(r, flavor_match=m))
        # Сортировка устойчивая: при равном совпадении остаётся порядок из sort
        matched.sort(key=lambda r: (-len(r.flavor_match.flavors), -r.flavor_match.share))
        return matched + undescribed

    async def get_tea(self, tea_id: int) -> Tea:
        tea = await self.db.get(Tea, tea_id)
        if not tea:
            raise TeaNotFoundError
        return tea

    async def get_offer(self, tea_id: int, shop_id: int) -> Offer:
        """Чай tea_id в магазине shop_id. Если магазин его не продаёт — 404."""
        offer = await self.db.scalar(select(Offer).where(Offer.tea_id == tea_id, Offer.shop_id == shop_id))
        if not offer:
            await self.get_tea(tea_id)  # сначала «чай не найден», если дело в нём
            raise OfferNotFoundError
        return offer

    async def tea(self, tea_id: int) -> TeaDetails:
        tea = await self.get_tea(tea_id)
        reviews = list(
            await self.db.scalars(select(Review).where(Review.tea_id == tea_id).order_by(Review.created_at.desc()))
        )
        same_category = await self.teas(category_id=tea.category_id)
        ranking = rank_shops(await self.scores.by_shop_and_category(category_id=tea.category_id))
        place = {s.shop_id: i + 1 for i, s in enumerate(ranking)}
        offer_scores = await self.scores.for_offers(tea_ids=[tea.id])
        offers = [
            RatedOffer(
                offer=o, score=offer_scores.get((o.tea_id, o.shop_id), EMPTY_SCORE), shop_rank=place.get(o.shop_id)
            )
            for o in tea.offers
        ]
        return TeaDetails(
            rated=next(r for r in same_category if r.tea.id == tea.id),
            offers=best_first(offers, lambda r: r.score),
            reviews=reviews,
            alternatives=[r for r in same_category if r.tea.id != tea.id][: self.ALTERNATIVES_LIMIT],
            flavors=FlavorProfile.of([r.flavors for r in reviews]),
            infusion=InfusionStats.of(reviews),
        )


def per_gram(tea: Tea) -> float | None:
    """Цена за грамм в самом дешёвом магазине, где цена известна."""
    prices = [o.price / o.weight for o in tea.offers if o.price is not None and o.weight]
    return min(prices) if prices else None


def _search(q: str):
    """Условие поиска: название и регион чая, магазин, вид чая, дескрипторы из отзывов."""
    pattern = f"%{_escape_like(q)}%"
    needle = q.casefold()
    # Вид чая и дескрипторы — enum'ы, ILIKE к ним не применить: ищем по подписям в Python («габ» → GABA)
    kinds = [k for k in TeaKind if needle in k.value.casefold() or needle in k.plural.casefold()]
    flavors = [f for f in Flavor if needle in f.value.casefold()]
    conditions = [
        Tea.title.ilike(pattern, escape="\\"),
        Tea.region.ilike(pattern, escape="\\"),
        Tea.id.in_(select(Offer.tea_id).join(Offer.shop).where(Shop.title.ilike(pattern, escape="\\"))),
    ]
    if kinds:
        conditions.append(Tea.category_id.in_(select(Category.id).where(Category.name.in_(kinds))))
    if flavors:
        conditions.append(Tea.id.in_(select(Review.tea_id).where(Review.flavors.overlap(flavors))))
    return or_(*conditions)


def _mean(scores: list[Score]) -> float:
    """Средняя по всем отзывам (а не средняя средних)."""
    total = sum(s.reviews for s in scores)
    return sum(s.avg * s.reviews for s in scores) / total if total else 0.0


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
