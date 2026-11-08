from typing import ClassVar

from fastapi import status

from back.core.auth import CurrentUser
from back.core.deps import DiaryDep
from back.core.views import View
from back.schemas.diary import DiaryEntryIn, DiaryEntryOut


class DiaryView(View):
    """Дневник текущего пользователя."""

    paths = ("",)
    method_options: ClassVar[dict] = {"post": {"status_code": status.HTTP_201_CREATED}}

    async def get(self, user: CurrentUser, diary: DiaryDep) -> list[DiaryEntryOut]:
        return [DiaryEntryOut.of(x) for x in await diary.entries(user)]

    async def post(self, data: DiaryEntryIn, user: CurrentUser, diary: DiaryDep) -> DiaryEntryOut:
        item = await diary.add(
            user,
            data.tea_id,
            data.shop_id,
            day=data.date,
            rating=data.rating,
            water=data.water,
            grams=data.grams,
            volume=data.volume,
            infusions=data.infusions,
            text=data.text,
        )
        return DiaryEntryOut.of(item)


class DiaryEntryView(View):
    paths = ("/{entry_id}",)
    route_options: ClassVar[dict] = {"status_code": status.HTTP_204_NO_CONTENT}

    async def delete(self, entry_id: int, user: CurrentUser, diary: DiaryDep) -> None:
        await diary.delete(user, entry_id)
