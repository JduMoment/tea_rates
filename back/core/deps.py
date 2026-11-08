"""Сервисы как зависимости FastAPI: один экземпляр на запрос, с сессией БД этого запроса."""

from typing import Annotated

from fastapi import Depends

from back.core.db import DbSession
from back.services.brewing import BrewingService
from back.services.catalog import CatalogService
from back.services.diary import DiaryService
from back.services.flavors import FlavorStatsService
from back.services.photos import PhotoService
from back.services.prices import PriceHistoryService
from back.services.rankings import RankingService
from back.services.recommendations import RecommendationService
from back.services.reviews import ReviewService
from back.services.shelf import ShelfService
from back.services.social import SocialService
from back.services.teas import TeaEditorService


def get_catalog(db: DbSession) -> CatalogService:
    return CatalogService(db)


def get_rankings(db: DbSession) -> RankingService:
    return RankingService(db)


def get_reviews(db: DbSession) -> ReviewService:
    return ReviewService(db)


def get_diary(db: DbSession) -> DiaryService:
    return DiaryService(db)


def get_tea_editor(db: DbSession) -> TeaEditorService:
    return TeaEditorService(db)


def get_flavor_stats(db: DbSession) -> FlavorStatsService:
    return FlavorStatsService(db)


def get_recommendations(db: DbSession) -> RecommendationService:
    return RecommendationService(db)


def get_brewing(db: DbSession) -> BrewingService:
    return BrewingService(db)


def get_prices(db: DbSession) -> PriceHistoryService:
    return PriceHistoryService(db)


def get_shelf(db: DbSession) -> ShelfService:
    return ShelfService(db)


def get_social(db: DbSession) -> SocialService:
    return SocialService(db)


def get_photos(db: DbSession) -> PhotoService:
    return PhotoService(db)


CatalogDep = Annotated[CatalogService, Depends(get_catalog)]
RankingsDep = Annotated[RankingService, Depends(get_rankings)]
ReviewsDep = Annotated[ReviewService, Depends(get_reviews)]
DiaryDep = Annotated[DiaryService, Depends(get_diary)]
TeaEditorDep = Annotated[TeaEditorService, Depends(get_tea_editor)]
FlavorStatsDep = Annotated[FlavorStatsService, Depends(get_flavor_stats)]
RecommendationsDep = Annotated[RecommendationService, Depends(get_recommendations)]
BrewingDep = Annotated[BrewingService, Depends(get_brewing)]
PricesDep = Annotated[PriceHistoryService, Depends(get_prices)]
ShelfDep = Annotated[ShelfService, Depends(get_shelf)]
SocialDep = Annotated[SocialService, Depends(get_social)]
PhotosDep = Annotated[PhotoService, Depends(get_photos)]
