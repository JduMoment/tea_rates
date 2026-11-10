"""Личный чайный дневник. Видит и меняет только хозяин."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from back.enums.shelf import ShelfStatus
from back.models import DiaryEntry, ShelfItem, User
from back.services.catalog import CatalogService, RatedTea
from back.services.errors import DiaryEntryNotFoundError


@dataclass(frozen=True, slots=True)
class DiaryItem:
    entry: DiaryEntry
    tea: RatedTea


class DiaryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.catalog = CatalogService(db)

    async def entries(self, user: User) -> list[DiaryItem]:
        entries = list(
            await self.db.scalars(
                select(DiaryEntry)
                .where(DiaryEntry.user_id == user.id)
                .order_by(DiaryEntry.date.desc(), DiaryEntry.created_at.desc())
            )
        )
        rated = {r.tea.id: r for r in await self.catalog.rate(list({e.tea.id: e.tea for e in entries}.values()))}
        return [DiaryItem(entry=e, tea=rated[e.tea_id]) for e in entries]

    async def add(
        self,
        user: User,
        tea_id: int,
        shop_id: int,
        *,
        day: date,
        rating: int,
        water: int,
        grams: Decimal,
        volume: int | None,
        infusions: int,
        text: str,
    ) -> DiaryItem:
        offer = await self.catalog.get_offer(tea_id, shop_id)
        entry = user.add_diary_entry(
            offer, date=day, rating=rating, water=water, grams=grams, volume=volume, infusions=infusions, text=text
        )
        self.db.add(entry)
        await self._shelve(user, tea_id)
        await self.db.commit()
        await self.db.refresh(entry)
        [rated] = await self.catalog.rate([await self.catalog.get_tea(tea_id)])
        return DiaryItem(entry=entry, tea=rated)

    async def _shelve(self, user: User, tea_id: int) -> None:
        """Заварил чай из «хочу попробовать», «хочу повторить» или не из шкафа вовсе — значит, он есть дома."""
        item = await self.db.get(ShelfItem, (user.id, tea_id))
        if item is None:
            self.db.add(ShelfItem(user_id=user.id, tea_id=tea_id, status=ShelfStatus.HAVE))
        elif item.status in (ShelfStatus.WANT, ShelfStatus.REPEAT):
            item.status = ShelfStatus.HAVE

    async def delete(self, user: User, entry_id: int) -> None:
        entry = await self.db.get(DiaryEntry, entry_id)
        if not entry or not user.owns(entry):
            raise DiaryEntryNotFoundError
        await self.db.delete(entry)
        await self.db.commit()
