from typing import Annotated

from fastapi import Query

from back.core.deps import RankingsDep
from back.core.views import View
from back.schemas.catalog import TeaOut
from back.schemas.rankings import CategoryLeaderOut, CategoryRankingRowOut, ShopRankingRowOut


class CategoryRankingView(View):
    """У кого брать этот вид чая: магазины по оценке их чаёв этого вида."""

    paths = ("/categories/{slug}",)

    async def get(self, slug: str, rankings: RankingsDep) -> list[CategoryRankingRowOut]:
        return [CategoryRankingRowOut.of(r) for r in await rankings.by_category(slug)]


class CategoryLeadersView(View):
    """Лидер каждого вида чая — для главной."""

    paths = ("/leaders",)

    async def get(self, rankings: RankingsDep) -> list[CategoryLeaderOut]:
        return [CategoryLeaderOut.of(x) for x in await rankings.leaders()]


class ShopRankingView(View):
    paths = ("/shops",)

    async def get(self, rankings: RankingsDep) -> list[ShopRankingRowOut]:
        return [ShopRankingRowOut.of(r) for r in await rankings.shops()]


class TopTeasView(View):
    """Топ чаёв: /api/rankings/teas?category=gaba&category=red&limit=20"""

    paths = ("/teas",)

    async def get(
        self,
        rankings: RankingsDep,
        category: Annotated[list[str], Query(max_length=16)] = [],  # noqa: B006 — FastAPI копирует значение
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> list[TeaOut]:
        return [TeaOut.of(t) for t in await rankings.teas(category, limit)]
