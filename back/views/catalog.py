from typing import Annotated, ClassVar

from fastapi import HTTPException, Query, UploadFile, status

from back.core.auth import CurrentUser, OptionalUser
from back.core.deps import (
    BrewingDep,
    CatalogDep,
    CatalogImagesDep,
    FlavorStatsDep,
    PricesDep,
    RecommendationsDep,
    ReviewsDep,
    ShopEditorDep,
    TeaEditorDep,
)
from back.core.views import View
from back.enums.flavor import Flavor
from back.schemas.brewing import BrewingOut
from back.schemas.catalog import (
    CategoryOut,
    ImageOut,
    OfferCreateIn,
    OfferIn,
    RecommendationsOut,
    ShopCheckOut,
    ShopDetailsOut,
    ShopIn,
    ShopPricesOut,
    ShopSummaryOut,
    TeaIn,
    TeaOut,
    TeaPatchIn,
)
from back.schemas.flavors import FlavorProfileOut, FlavorWheelOut
from back.schemas.reviews import TeaDetailsOut
from back.services.catalog import TeaSort
from back.services.photos import MAX_BYTES, PhotoError


class CategoriesView(View):
    paths = ("/categories",)

    async def get(self, catalog: CatalogDep) -> list[CategoryOut]:
        return [CategoryOut.of(c) for c in await catalog.categories()]


class FlavorWheelView(View):
    """Колесо вкусов целиком: вкусы, группы, дескрипторы, цвета. Не меняется без деплоя — можно кешировать."""

    paths = ("/flavors",)

    async def get(self) -> FlavorWheelOut:
        return FlavorWheelOut.build()


class ShopsView(View):
    """Все магазины. POST — добавить магазин (сайт обязателен и уникален: 409, если такой уже есть)."""

    paths = ("/shops",)
    method_options: ClassVar[dict] = {"post": {"status_code": status.HTTP_201_CREATED}}

    async def get(self, catalog: CatalogDep) -> list[ShopSummaryOut]:
        return [ShopSummaryOut.of(s) for s in await catalog.shops()]

    async def post(self, data: ShopIn, user: CurrentUser, editor: ShopEditorDep, catalog: CatalogDep) -> ShopDetailsOut:
        shop = await editor.create(
            user, title=data.title, site=data.site, city=data.city, country=data.country, description=data.description
        )
        return ShopDetailsOut.of(await catalog.shop(shop.name))


class ShopCheckView(View):
    """Перед добавлением магазина: /api/shops/check?title=…&site=… — есть ли такой сайт и похожие названия."""

    paths = ("/shops/check",)

    async def get(
        self,
        editor: ShopEditorDep,
        title: Annotated[str, Query(max_length=128)] = "",
        site: Annotated[str, Query(max_length=512)] = "",
    ) -> ShopCheckOut:
        return ShopCheckOut.of(await editor.check(title, site))


class ShopView(View):
    paths = ("/shops/{name}",)

    async def get(self, name: str, catalog: CatalogDep) -> ShopDetailsOut:
        return ShopDetailsOut.of(await catalog.shop(name))


async def _upload(file: UploadFile, save) -> ImageOut:
    try:
        stored = await save(await file.read(MAX_BYTES + 1))
    except PhotoError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from None
    return ImageOut(url=stored.url, thumb_url=stored.thumb_url)


class ShopLogoView(View):
    """Логотип магазина (multipart, поле file; JPEG, PNG или WebP до 10 МБ). Любой вошедший,
    пока логотипа нет. Заменить или удалить нельзя."""

    paths = ("/shops/{shop_id}/logo",)

    async def put(self, shop_id: int, file: UploadFile, user: CurrentUser, images: CatalogImagesDep) -> ImageOut:
        return await _upload(file, lambda data: images.set_shop_logo(shop_id, data))


class TeaImageView(View):
    """Фото чая (multipart, поле file; JPEG, PNG или WebP до 10 МБ). Любой вошедший,
    пока фото нет. Заменить или удалить нельзя."""

    paths = ("/teas/{tea_id}/image",)

    async def put(self, tea_id: int, file: UploadFile, user: CurrentUser, images: CatalogImagesDep) -> ImageOut:
        return await _upload(file, lambda data: images.set_tea_image(tea_id, data))


class TeasView(View):
    """Каталог чаёв с фильтрами: /api/teas?category=gaba&shop=daochain&q=мёд&sort=rating
    Поиск по вкусу: &flavor=honey&flavor=peach — чаи, где слышат хоть одну из нот (у них есть flavorMatch),
    за ними чаи, о вкусе которых ещё не писали (flavorMatch: null).
    POST — добавить чай (сразу с магазином, где он продаётся)."""

    paths = ("/teas",)
    method_options: ClassVar[dict] = {"post": {"status_code": status.HTTP_201_CREATED}}

    async def get(
        self,
        catalog: CatalogDep,
        category: Annotated[str | None, Query(max_length=32)] = None,
        shop: Annotated[str | None, Query(max_length=64)] = None,
        q: Annotated[str | None, Query(max_length=100)] = None,
        flavor: Annotated[list[str], Query(max_length=len(Flavor))] = [],  # noqa: B006 — так FastAPI читает список
        sort: TeaSort = TeaSort.RATING,
    ) -> list[TeaOut]:
        category_id = (await catalog.category(category)).id if category else None
        shop_id = (await catalog.get_shop(shop)).id if shop else None
        flavors = [Flavor.from_slug(f) for f in flavor]
        if None in flavors:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Неизвестная нота вкуса")
        teas = await catalog.teas(category_id=category_id, shop_id=shop_id, q=q, flavors=flavors, sort=sort)
        return [TeaOut.of(t) for t in teas]

    async def post(self, data: TeaIn, user: CurrentUser, editor: TeaEditorDep) -> TeaDetailsOut:
        details = await editor.create(
            user, category_slug=data.category, tea=data.fields(), shop_id=data.shop_id, offer=data.offer.fields()
        )
        return TeaDetailsOut.of(details)


class TeaView(View):
    """Страница чая. PATCH — только автор и только пока нет чужих отзывов. Удалять чай из каталога нельзя."""

    paths = ("/teas/{tea_id}",)

    async def get(self, tea_id: int, catalog: CatalogDep, reviews: ReviewsDep, user: OptionalUser) -> TeaDetailsOut:
        details = await catalog.tea(tea_id)
        ids = [r.id for r in details.reviews]
        return TeaDetailsOut.of(details, voted=await reviews.voted(user, ids), experience=await reviews.experience(ids))

    async def patch(self, tea_id: int, data: TeaPatchIn, user: CurrentUser, editor: TeaEditorDep) -> TeaDetailsOut:
        return TeaDetailsOut.of(await editor.update(user, tea_id, data.fields()))


class TeaFlavorsView(View):
    """Вкусовой профиль чая по отзывам: всех магазинов или одного (?shop=art-of-tea)."""

    paths = ("/teas/{tea_id}/flavors",)

    async def get(
        self,
        tea_id: int,
        catalog: CatalogDep,
        stats: FlavorStatsDep,
        shop: Annotated[str | None, Query(max_length=64)] = None,
    ) -> FlavorProfileOut:
        await catalog.get_tea(tea_id)
        shop_id = (await catalog.get_shop(shop)).id if shop else None
        return FlavorProfileOut.of(await stats.for_tea(tea_id, shop_id))


class TeaBrewingView(View):
    """Как заваривают чай: медианы по дневникам всех пользователей или типичное для вида чая."""

    paths = ("/teas/{tea_id}/brewing",)

    async def get(self, tea_id: int, catalog: CatalogDep, brewing: BrewingDep) -> BrewingOut:
        return BrewingOut.of(await brewing.for_tea(await catalog.get_tea(tea_id)))


class TeaPricesView(View):
    """История цены чая по магазинам: из отзывов с ценой покупки и стартовой цены предложения."""

    paths = ("/teas/{tea_id}/prices",)

    async def get(self, tea_id: int, catalog: CatalogDep, prices: PricesDep) -> list[ShopPricesOut]:
        return [ShopPricesOut.of(sp) for sp in await prices.for_tea(await catalog.get_tea(tea_id))]


class UserFlavorsView(View):
    """Вкусовой профиль пользователя: что он отмечал в своих отзывах (отзывы публичные — и профиль тоже)."""

    paths = ("/users/{user_id}/flavors",)

    async def get(self, user_id: int, stats: FlavorStatsDep) -> FlavorProfileOut:
        return FlavorProfileOut.of(await stats.for_user(user_id))


class RecommendationsView(View):
    """«Вам может понравиться» для текущего пользователя — по нотам из его отзывов."""

    paths = ("/me/recommendations",)

    async def get(
        self, user: CurrentUser, recommendations: RecommendationsDep, limit: Annotated[int, Query(ge=1, le=50)] = 12
    ) -> RecommendationsOut:
        return RecommendationsOut.of(await recommendations.for_user(user.id, limit))


class OffersView(View):
    """Добавить магазин, где продаётся чай."""

    paths = ("/teas/{tea_id}/offers",)
    route_options: ClassVar[dict] = {"status_code": status.HTTP_201_CREATED}

    async def post(self, tea_id: int, data: OfferCreateIn, user: CurrentUser, editor: TeaEditorDep) -> TeaDetailsOut:
        return TeaDetailsOut.of(await editor.add_offer(user, tea_id, data.shop_id, data.fields()))


class OfferView(View):
    """Править магазин у чая — только автор предложения и пока нет чужих отзывов на покупку там. Убрать нельзя."""

    paths = ("/teas/{tea_id}/offers/{shop_id}",)

    async def patch(
        self, tea_id: int, shop_id: int, data: OfferIn, user: CurrentUser, editor: TeaEditorDep
    ) -> TeaDetailsOut:
        return TeaDetailsOut.of(await editor.update_offer(user, tea_id, shop_id, data.fields()))
