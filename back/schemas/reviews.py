from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, Field, field_validator

from back.models import Review
from back.models.review import Infusion, Purchase
from back.schemas.base import ApiModel
from back.schemas.catalog import HarvestIn, PriceIn, RatedOfferOut, ShopBriefOut, TeaOut
from back.schemas.flavors import FlavorProfileOut, FlavorsIn
from back.services.catalog import InfusionStats, RatedTea, TeaDetails


def _check_rating(v: int) -> int:
    if not 1 <= v <= 5:
        raise ValueError("Поставьте оценку от 1 до 5")
    return v


#: Оценка 1–5 (листики на сайте).
Rating = Annotated[int, AfterValidator(_check_rating)]


def _check_scale(v: int | None) -> int | None:
    if v is not None and not 1 <= v <= 5:
        raise ValueError("Шкала настоя — от 1 до 5")
    return v


#: Шкала настоя 1–5 или null — не оценивал.
Scale = Annotated[int | None, AfterValidator(_check_scale)]


class ReviewIn(PriceIn, HarvestIn):
    """Отзыв на покупку. Цена (price + weight) и партия (harvest_*) — необязательные сведения о ней."""

    #: Где куплен чай. Обязателен: от него зависит рейтинг магазина.
    shop_id: int
    rating: Rating
    text: str
    #: Slug'и дескрипторов колеса: ["honey", "citrus"]. Группу и вкус бэкенд выводит сам.
    flavors: FlavorsIn = Field(default_factory=list)
    #: Настой: тело (лёгкий → плотный), насыщенность (пустой → крепкий), послевкусие (короткое → долгое).
    body: Scale = None
    strength: Scale = None
    aftertaste: Scale = None

    @field_validator("text")
    @classmethod
    def check_text(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Напишите хотя бы пару слов (от 10 символов)")
        if len(v) > 4000:
            raise ValueError("Слишком длинный отзыв — до 4000 символов")
        return v

    def infusion(self) -> Infusion:
        return Infusion(body=self.body, strength=self.strength, aftertaste=self.aftertaste)

    def purchase(self) -> Purchase:
        return Purchase(
            price=self.price, weight=self.weight, harvest_year=self.harvest_year, harvest_season=self.season
        )


class VoteIn(ApiModel):
    helpful: bool


class ReviewAuthorOut(ApiModel):
    id: int
    name: str


class ReviewOut(ApiModel):
    id: int
    tea_id: int
    shop_id: int
    user_id: int
    rating: int
    text: str
    #: Slug'и дескрипторов
    flavors: list[str]
    created_at: datetime
    #: Покупка: цена в рублях за weight граммов и партия. Всё может быть null.
    price: int | None
    weight: int | None
    #: «1 450 ₽ / 50 г»
    price_label: str | None
    harvest_year: int | None
    #: spring / summer / autumn / winter
    harvest_season: str | None
    #: «Весна 2025», «2018» или пустая строка
    harvest: str
    body: int | None
    strength: int | None
    aftertaste: int | None
    #: Сколько человек отметили отзыв полезным; voted — отметил ли текущий пользователь.
    helpful: int
    voted: bool = False
    photos: list["PhotoOut"] = Field(default_factory=list)
    user: ReviewAuthorOut
    shop: ShopBriefOut
    #: Есть в лентах (свежие отзывы, отзывы пользователя); на странице чая — нет, он и так известен.
    tea: TeaOut | None = None

    @classmethod
    def of(cls, r: Review, tea: RatedTea | None = None, voted: set[int] = frozenset()) -> "ReviewOut":
        return cls(
            id=r.id,
            tea_id=r.tea_id,
            shop_id=r.shop_id,
            user_id=r.user_id,
            rating=r.rating,
            text=r.text,
            flavors=[f.slug for f in r.flavors],
            created_at=r.created_at,
            price=r.price,
            weight=r.weight,
            price_label=r.price_label,
            harvest_year=r.harvest_year,
            harvest_season=r.harvest_season.slug if r.harvest_season else None,
            harvest=r.harvest,
            body=r.body,
            strength=r.strength,
            aftertaste=r.aftertaste,
            helpful=r.helpful or 0,
            voted=r.id in voted,
            photos=[PhotoOut.of(p) for p in r.photos],
            user=ReviewAuthorOut(id=r.user.id, name=r.user.name),
            shop=ShopBriefOut.of(r.shop),
            tea=TeaOut.of(tea) if tea else None,
        )


class PhotoOut(ApiModel):
    id: int
    url: str
    thumb_url: str
    width: int
    height: int

    @classmethod
    def of(cls, p) -> "PhotoOut":
        from back.core.storage import storage

        return cls(id=p.id, url=storage.url(p.key), thumb_url=storage.url(p.thumb_key), width=p.width, height=p.height)


class InfusionStatsOut(ApiModel):
    """Средние шкалы настоя по отзывам (null — никто не отметил)."""

    body: float | None
    strength: float | None
    aftertaste: float | None
    reviews: int

    @classmethod
    def of(cls, s: InfusionStats) -> "InfusionStatsOut":
        return cls(body=s.body, strength=s.strength, aftertaste=s.aftertaste, reviews=s.reviews)


class TeaDetailsOut(TeaOut):
    """Страница чая: чай + где купить (с оценкой в каждом магазине) + отзывы + вкусовой профиль
    + другие чаи этого вида."""

    #: Перекрывает TeaOut.offers: здесь у каждого магазина своя оценка и место в рейтинге вида.
    offers: list[RatedOfferOut]
    reviews: list[ReviewOut]
    alternatives: list[TeaOut]
    flavor_profile: FlavorProfileOut
    infusion: InfusionStatsOut

    @classmethod
    def of(cls, details: TeaDetails, voted: set[int] = frozenset()) -> "TeaDetailsOut":
        return cls(
            **TeaOut.of(details.rated).model_dump(exclude={"offers"}),
            offers=[RatedOfferOut.of(o) for o in details.offers],
            reviews=[ReviewOut.of(r, voted=voted) for r in details.reviews],
            infusion=InfusionStatsOut.of(details.infusion),
            alternatives=[TeaOut.of(t) for t in details.alternatives],
            flavor_profile=FlavorProfileOut.of(details.flavors),
        )
