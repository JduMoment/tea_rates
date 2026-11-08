"""История цены чая по магазинам: цены из отзывов (когда купили и почём) и стартовая цена предложения."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from back.models import Review, Shop, Tea


@dataclass(frozen=True, slots=True)
class PricePoint:
    at: datetime
    price: int
    weight: int
    #: review — цена покупки из отзыва; offer — цена на сайте, указанная при добавлении магазина.
    source: str

    @property
    def per_gram(self) -> float:
        return self.price / self.weight


@dataclass(frozen=True, slots=True)
class ShopPrices:
    shop: Shop
    #: По времени, старые первыми.
    points: list[PricePoint]


class PriceHistoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def for_tea(self, tea: Tea) -> list[ShopPrices]:
        rows = await self.db.execute(
            select(Review.shop_id, Review.created_at, Review.price, Review.weight)
            .where(Review.tea_id == tea.id, Review.price.is_not(None))
            .order_by(Review.created_at)
        )
        by_shop: dict[int, list[PricePoint]] = {o.shop_id: [] for o in tea.offers}
        for shop_id, at, price, weight in rows:
            by_shop.setdefault(shop_id, []).append(PricePoint(at=at, price=price, weight=weight, source="review"))
        result = []
        for offer in tea.offers:
            points = by_shop[offer.shop_id]
            if offer.start_price is not None:
                start = PricePoint(offer.created_at, offer.start_price, offer.start_weight, "offer")
                points = sorted([start, *points], key=lambda p: p.at)
            if points:
                result.append(ShopPrices(shop=offer.shop, points=points))
        return result
