from back.schemas.base import ApiModel
from back.schemas.catalog import CategoryOut, RatedOfferOut, ShopCategoryScoreOut, ShopOut, ShopSummaryOut, TeaOut
from back.services.rankings import CategoryLeader, CategoryRankingRow, ShopRankingRow


class CategoryRankingRowOut(ApiModel):
    shop: ShopOut
    score: ShopCategoryScoreOut
    #: Лучший чай вида у магазина; stats — по всем магазинам.
    best_tea: TeaOut
    #: Он же в этом магазине: цена и оценка покупок именно здесь.
    best_offer: RatedOfferOut

    @classmethod
    def of(cls, row: CategoryRankingRow) -> "CategoryRankingRowOut":
        return cls(
            shop=ShopOut.of(row.shop),
            score=ShopCategoryScoreOut.of(row.score),
            best_tea=TeaOut.of(row.best_tea),
            best_offer=RatedOfferOut.of(row.best_offer),
        )


class CategoryLeaderOut(ApiModel):
    category: CategoryOut
    leader: CategoryRankingRowOut

    @classmethod
    def of(cls, item: CategoryLeader) -> "CategoryLeaderOut":
        return cls(category=CategoryOut.of(item.category), leader=CategoryRankingRowOut.of(item.leader))


class ShopRankingRowOut(ApiModel):
    shop: ShopSummaryOut
    leads: list[int]
    scores: list[ShopCategoryScoreOut]

    @classmethod
    def of(cls, row: ShopRankingRow) -> "ShopRankingRowOut":
        return cls(
            shop=ShopSummaryOut.of(row.summary),
            leads=row.leads,
            scores=[ShopCategoryScoreOut.of(s) for s in row.scores],
        )
