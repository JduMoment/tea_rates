"""Рейтинги: магазины внутри вида чая, магазины в целом, лучшие отдельные чаи."""

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from back.models import Category, Offer, Shop, Tea
from back.services.catalog import CatalogService, RatedOffer, RatedTea, ShopSummary, rank_shops
from back.services.scoring import EMPTY_SCORE, ShopCategoryScore, best_first


@dataclass(frozen=True, slots=True)
class CategoryRankingRow:
    shop: Shop
    score: ShopCategoryScore
    #: Лучший чай этого вида у магазина — «что именно у них брать» (оценка — по всем магазинам).
    best_tea: RatedTea
    #: Он же именно в этом магазине: цена и оценка по покупкам здесь.
    best_offer: RatedOffer


@dataclass(frozen=True, slots=True)
class CategoryLeader:
    category: Category
    leader: CategoryRankingRow


@dataclass(frozen=True, slots=True)
class ShopRankingRow:
    summary: ShopSummary
    #: Виды чая, где магазин на первом месте.
    leads: list[int]
    #: Оценки по всем видам чая магазина, лучшие первыми.
    scores: list[ShopCategoryScore]


class RankingService:
    TOP_TEAS_DEFAULT = 20

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.catalog = CatalogService(db)

    async def by_category(self, slug: str) -> list[CategoryRankingRow]:
        """Какой магазин лучше всего делает этот вид чая."""
        category = await self.catalog.category(slug)
        scores = await self.catalog.scores.by_shop_and_category(category_id=category.id)
        return await self._rows(scores, category_id=category.id)

    async def leaders(self) -> list[CategoryLeader]:
        """Лидер в каждом виде чая (для главной). Виды без отзывов пропускаются."""
        categories = await self.catalog.categories()
        rows_by_cat: dict[int, list[CategoryRankingRow]] = defaultdict(list)
        for row in await self._rows(await self.catalog.scores.by_shop_and_category()):
            rows_by_cat[row.score.category_id].append(row)

        out = []
        for category in categories:
            rows = rows_by_cat[category.id]  # _rows уже отсортировал лучших первыми
            if rows and rows[0].score.score.reviews > 0:
                out.append(CategoryLeader(category=category, leader=rows[0]))
        return out

    async def shops(self) -> list[ShopRankingRow]:
        """Магазины по общей оценке их чаёв."""
        scores_by_shop: dict[int, list[ShopCategoryScore]] = defaultdict(list)
        scores_by_cat: dict[int, list[ShopCategoryScore]] = defaultdict(list)
        for s in await self.catalog.scores.by_shop_and_category():
            scores_by_shop[s.shop_id].append(s)
            scores_by_cat[s.category_id].append(s)

        leads: dict[int, list[int]] = defaultdict(list)
        for category in await self.catalog.categories():
            ranked = rank_shops(scores_by_cat[category.id])
            if ranked and ranked[0].score.reviews > 0:
                leads[ranked[0].shop_id].append(category.id)

        rows = [
            ShopRankingRow(summary=s, leads=leads[s.shop.id], scores=rank_shops(scores_by_shop[s.shop.id]))
            for s in await self.catalog.shops()
        ]
        return best_first(rows, lambda r: r.summary.score)

    async def teas(self, slugs: list[str] | None = None, limit: int = TOP_TEAS_DEFAULT) -> list[RatedTea]:
        """Лучшие отдельные чаи («Топ-20»). Пустой список видов — все виды. Чаи без отзывов не попадают."""
        wanted = {(await self.catalog.category(slug)).id for slug in slugs or []}
        rated = [
            r for r in await self.catalog.teas() if r.score.reviews > 0 and (not wanted or r.tea.category_id in wanted)
        ]
        return rated[:limit]  # catalog.teas() уже отсортирован по сглаженной оценке

    async def _rows(self, scores: list[ShopCategoryScore], category_id: int | None = None) -> list[CategoryRankingRow]:
        """Строки рейтинга «магазин × вид», лучшие первыми, с лучшим чаем магазина в каждой."""
        best = await self._best_offers(category_id)
        rated_teas = {r.tea.id: r for r in await self.catalog.rate([o.offer.tea for o in best.values()])}
        rows = []
        for s in rank_shops(scores):
            offer = best.get((s.category_id, s.shop_id))
            if offer:  # у каждой строки scores есть хоть одно предложение, но не полагаемся на это молча
                rows.append(
                    CategoryRankingRow(
                        shop=offer.offer.shop, score=s, best_tea=rated_teas[offer.offer.tea_id], best_offer=offer
                    )
                )
        return rows

    async def _best_offers(self, category_id: int | None) -> dict[tuple[int, int], RatedOffer]:
        """(вид, магазин) → лучшее предложение магазина в этом виде по оценкам покупок в нём."""
        # Цикл Offer → Tea → offers SQLAlchemy сам жадно не грузит — указываем путь явно
        query = (
            select(Offer)
            .join(Offer.tea)
            .options(selectinload(Offer.tea).selectinload(Tea.offers).joinedload(Offer.shop))
        )
        if category_id is not None:
            query = query.where(Tea.category_id == category_id)
        offers = list(await self.db.scalars(query))
        scores = await self.catalog.scores.for_offers(category_id=category_id)
        rated = [RatedOffer(offer=o, score=scores.get((o.tea_id, o.shop_id), EMPTY_SCORE)) for o in offers]
        best: dict[tuple[int, int], RatedOffer] = {}
        for r in best_first(rated, lambda r: r.score):  # первый встреченный и есть лучший
            best.setdefault((r.offer.tea.category_id, r.offer.shop_id), r)
        return best
