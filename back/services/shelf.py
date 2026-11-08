"""«Мои чаи» — личный шкаф: что хочу попробовать, что есть дома, что закончилось."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from back.enums.shelf import ShelfStatus
from back.models import ShelfItem, Tea, User
from back.services.catalog import CatalogService, RatedTea


@dataclass(frozen=True, slots=True)
class Shelved:
    item: ShelfItem
    tea: RatedTea


class ShelfService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.catalog = CatalogService(db)

    async def items(self, user: User) -> list[Shelved]:
        items = list(
            await self.db.scalars(
                select(ShelfItem).where(ShelfItem.user_id == user.id).order_by(ShelfItem.updated_at.desc())
            )
        )
        teas = list(await self.db.scalars(select(Tea).where(Tea.id.in_([i.tea_id for i in items]))))
        rated = {r.tea.id: r for r in await self.catalog.rate(teas)}
        return [Shelved(item=i, tea=rated[i.tea_id]) for i in items]

    async def put(self, user: User, tea_id: int, status: ShelfStatus) -> Shelved:
        tea = await self.catalog.get_tea(tea_id)
        item = await self.db.get(ShelfItem, (user.id, tea_id))
        if item is None:
            item = ShelfItem(user_id=user.id, tea_id=tea_id, status=status)
            self.db.add(item)
        else:
            item.status = status
        await self.db.commit()
        await self.db.refresh(item)
        [rated] = await self.catalog.rate([tea])
        return Shelved(item=item, tea=rated)

    async def remove(self, user: User, tea_id: int) -> None:
        item = await self.db.get(ShelfItem, (user.id, tea_id))
        if item:
            await self.db.delete(item)
            await self.db.commit()
