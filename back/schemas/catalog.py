from datetime import UTC, datetime
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from back.core.shop_url import BadShopUrl, shop_key
from back.core.storage import storage
from back.enums.season import Season
from back.models import Category, Offer, Shop
from back.schemas.base import ApiModel
from back.services.catalog import RatedOffer, RatedTea, ShopDetails, ShopSummary
from back.services.flavors import FlavorMatch
from back.services.prices import ShopPrices
from back.services.recommendations import Recommendations
from back.services.scoring import Score, ShopCategoryScore
from back.services.shops import ShopCheck
from back.services.teas import OfferFields, TeaFields


def _url(key: str | None) -> str | None:
    return storage.url(key) if key else None


class ImageOut(ApiModel):
    """Загруженная картинка каталога: большая и превью (у логотипа совпадают)."""

    url: str
    thumb_url: str


class CategoryOut(ApiModel):
    """Вид чая. В БД только id и вид, остальное выводится из TeaKind."""

    id: int
    #: Для адресов и фильтров: /rankings/categories/gaba, ?category=gaba
    slug: str
    name: str
    plural: str
    instrumental: str
    color: str
    ink: str

    @classmethod
    def of(cls, c: Category) -> "CategoryOut":
        k = c.name
        return cls(
            id=c.id,
            slug=k.slug,
            name=k.value,
            plural=k.plural,
            instrumental=k.instrumental,
            color=k.color,
            ink=k.ink,
        )


class ShopBriefOut(ApiModel):
    """Магазин в отзывах и предложениях — только чтобы подписать и сослаться."""

    id: int
    #: Для адресов и фильтров: /shops/art-of-tea, ?shop=art-of-tea
    name: str
    title: str
    #: Логотип (WebP до 256 px); null — не загружен.
    logo_url: str | None

    @classmethod
    def of(cls, s: Shop) -> "ShopBriefOut":
        return cls(id=s.id, name=s.name, title=s.title, logo_url=_url(s.logo_key))


class ShopOut(ShopBriefOut):
    country: str
    city: str
    site: str
    founded: int | None
    description: str
    author_id: int | None

    @classmethod
    def of(cls, s: Shop) -> "ShopOut":
        return cls(
            **ShopBriefOut.of(s).model_dump(),
            author_id=s.author_id,
            country=s.country,
            city=s.city,
            site=s.site,
            founded=s.founded_year,
            description=s.description or "",
        )


class StatsOut(ApiModel):
    avg: float
    reviews: int

    @classmethod
    def of(cls, score: Score) -> "StatsOut":
        return cls(avg=round(score.shown, 2), reviews=score.reviews)


class OfferOut(ApiModel):
    """Чай в конкретном магазине."""

    id: int
    tea_id: int
    shop_id: int
    shop: ShopBriefOut
    #: Текущая цена в рублях за weight граммов: из последнего отзыва с ценой, иначе стартовая.
    #: Нет ни того, ни другого — null.
    price: int | None
    weight: int | None
    #: Готовая подпись: «1 450 ₽ / 50 г»
    price_label: str | None
    #: Когда цена была актуальна: дата отзыва или дата добавления магазина.
    price_date: datetime | None
    #: review — из отзыва, offer — указана при добавлении магазина.
    price_source: Literal["review", "offer"] | None
    url: str | None
    author_id: int | None

    @classmethod
    def of(cls, o: Offer) -> "OfferOut":
        return cls(
            id=o.id,
            tea_id=o.tea_id,
            shop_id=o.shop_id,
            shop=ShopBriefOut.of(o.shop),
            price=o.price,
            weight=o.weight,
            price_label=o.price_label,
            price_date=o.price_at,
            price_source=o.price_source,
            url=o.url,
            author_id=o.author_id,
        )


class RatedOfferOut(OfferOut):
    """Предложение с оценкой чая именно из этого магазина."""

    stats: StatsOut
    #: Место магазина в рейтинге по виду этого чая (только на странице чая).
    shop_rank: int | None

    @classmethod
    def of(cls, r: RatedOffer) -> "RatedOfferOut":
        return cls(**OfferOut.of(r.offer).model_dump(), stats=StatsOut.of(r.score), shop_rank=r.shop_rank)


class FlavorMatchOut(ApiModel):
    """Совпадение с нотами из поиска по вкусу."""

    #: slug'и выбранных нот, которые слышат в чае, — чаще упоминаемые первыми.
    flavors: list[str]
    #: Доля отзывов с нотами, где есть хоть одна из выбранных, от 0 до 1.
    share: float

    @classmethod
    def of(cls, m: FlavorMatch) -> "FlavorMatchOut":
        return cls(flavors=[f.slug for f in m.flavors], share=round(m.share, 3))


class TeaOut(ApiModel):
    """Чай в списках: сам чай + вид + где купить + общая оценка."""

    id: int
    name: str
    category_id: int
    title: str
    region: str | None
    description: str
    author_id: int | None
    #: Фото чая и его превью для карточек; null — не загружено.
    image_url: str | None
    thumb_url: str | None
    category: CategoryOut
    #: Магазины, где продаётся, дешёвые первыми.
    offers: list[OfferOut]
    stats: StatsOut
    #: Только при поиске по вкусу (?flavor=): null — о вкусе этого чая ещё не писали.
    flavor_match: FlavorMatchOut | None = None

    @classmethod
    def of(cls, rated: RatedTea) -> "TeaOut":
        t = rated.tea
        return cls(
            id=t.id,
            name=t.name,
            category_id=t.category_id,
            title=t.title,
            region=t.region,
            description=t.description,
            author_id=t.author_id,
            image_url=_url(t.image_key),
            thumb_url=_url(t.image_thumb_key),
            category=CategoryOut.of(t.category),
            offers=[OfferOut.of(o) for o in t.offers],
            stats=StatsOut.of(rated.score),
            flavor_match=FlavorMatchOut.of(rated.flavor_match) if rated.flavor_match else None,
        )


class PricePointOut(ApiModel):
    at: datetime
    price: int
    weight: int
    per_gram: float
    source: Literal["review", "offer"]


class ShopPricesOut(ApiModel):
    """История цены чая в одном магазине, старые точки первыми."""

    shop: ShopBriefOut
    points: list[PricePointOut]

    @classmethod
    def of(cls, sp: ShopPrices) -> "ShopPricesOut":
        return cls(
            shop=ShopBriefOut.of(sp.shop),
            points=[
                PricePointOut(at=p.at, price=p.price, weight=p.weight, per_gram=round(p.per_gram, 2), source=p.source)
                for p in sp.points
            ],
        )


class RecommendationOut(ApiModel):
    tea: TeaOut
    #: slug'и общих нот пользователя и чая — почему советуем.
    reasons: list[str]
    #: Похожесть вкуса, от 0 до 1.
    score: float


class RecommendationsOut(ApiModel):
    """«Вам может понравиться». Пока у пользователя меньше needed отзывов с нотами — items пустой."""

    reviews: int
    needed: int
    items: list[RecommendationOut]

    @classmethod
    def of(cls, r: Recommendations) -> "RecommendationsOut":
        return cls(
            reviews=r.reviews,
            needed=r.needed,
            items=[
                RecommendationOut(tea=TeaOut.of(i.rated), reasons=[f.slug for f in i.reasons], score=round(i.score, 3))
                for i in r.items
            ],
        )


class ShopCategoryScoreOut(ApiModel):
    """Средняя оценка магазина в одном виде чая."""

    shop_id: int
    category_id: int
    avg: float
    reviews: int
    teas: int

    @classmethod
    def of(cls, s: ShopCategoryScore) -> "ShopCategoryScoreOut":
        return cls(
            shop_id=s.shop_id,
            category_id=s.category_id,
            avg=round(s.score.shown, 2),
            reviews=s.score.reviews,
            teas=s.teas,
        )


class ShopSummaryOut(ShopOut):
    stats: StatsOut
    tea_count: int
    specialties: list[ShopCategoryScoreOut]

    @classmethod
    def of(cls, summary: ShopSummary) -> "ShopSummaryOut":
        return cls(
            **ShopOut.of(summary.shop).model_dump(),
            stats=StatsOut.of(summary.score),
            tea_count=summary.tea_count,
            specialties=[ShopCategoryScoreOut.of(s) for s in summary.specialties],
        )


class ShopDetailsOut(ShopSummaryOut):
    scores: list[ShopCategoryScoreOut]
    teas: list[TeaOut]

    @classmethod
    def of(cls, details: ShopDetails) -> "ShopDetailsOut":
        return cls(
            **ShopSummaryOut.of(details.summary).model_dump(),
            scores=[ShopCategoryScoreOut.of(s) for s in details.scores],
            teas=[TeaOut.of(t) for t in details.teas],
        )


# ---------- ввод: добавление и правка чаёв ----------


def _clean(v: str | None) -> str | None:
    return (v or "").strip() or None


class PriceIn(ApiModel):
    """Цена: сколько рублей за сколько граммов. Необязательна, но только вместе с весом."""

    price: int | None = Field(default=None, ge=1, le=10_000_000)
    weight: int | None = Field(default=None, ge=1, le=10_000)

    @model_validator(mode="after")
    def check_price_weight(self) -> Self:
        if (self.price is None) != (self.weight is None):
            raise ValueError("Укажите и цену, и вес — или ни то, ни другое")
        return self


class HarvestIn(ApiModel):
    """Партия: год и сезон сбора. Оба необязательны."""

    harvest_year: int | None = None
    #: spring / summer / autumn / winter
    harvest_season: str | None = None

    @field_validator("harvest_year")
    @classmethod
    def check_year(cls, v: int | None) -> int | None:
        if v is not None and not 1900 <= v <= datetime.now(UTC).year:
            raise ValueError("Год сбора — от 1900 до текущего")
        return v

    @field_validator("harvest_season")
    @classmethod
    def check_season(cls, v: str | None) -> str | None:
        v = _clean(v)
        if v is not None and Season.from_slug(v) is None:
            raise ValueError("Сезон сбора: spring, summer, autumn или winter")
        return v

    @property
    def season(self) -> Season | None:
        return Season.from_slug(self.harvest_season) if self.harvest_season else None


class OfferIn(PriceIn):
    """Магазин продаёт чай: ссылка и цена на сайте сейчас (дальше её обновляют отзывы).
    Магазин — из адреса или из TeaIn.shop_id."""

    url: str | None = Field(default=None, max_length=512)

    @field_validator("url")
    @classmethod
    def check_url(cls, v: str | None) -> str | None:
        v = _clean(v)
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("Ссылка должна начинаться с http:// или https://")
        return v

    def fields(self) -> OfferFields:
        return OfferFields(price=self.price, weight=self.weight, url=self.url)


class TeaPatchIn(ApiModel):
    """Правка самого чая (не магазина)."""

    title: str = Field(max_length=128)
    region: str | None = Field(default=None, max_length=128)
    description: str = Field(default="", max_length=4000)

    @field_validator("title")
    @classmethod
    def check_title(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 2:
            raise ValueError("Название слишком короткое")
        return v

    @field_validator("region")
    @classmethod
    def check_region(cls, v: str | None) -> str | None:
        return _clean(v)

    @field_validator("description")
    @classmethod
    def check_description(cls, v: str) -> str:
        return v.strip()

    def fields(self) -> TeaFields:
        return TeaFields(title=self.title, region=self.region, description=self.description)


class TeaIn(TeaPatchIn):
    """Новый чай сразу с первым магазином, где его продают."""

    #: Вид чая: gaba, red, …
    category: str = Field(max_length=32)
    shop_id: int
    offer: OfferIn


class OfferCreateIn(OfferIn):
    shop_id: int


class ShopIn(ApiModel):
    """Новый магазин. Сайт обязателен: по нему ловим дубли."""

    title: str = Field(max_length=128)
    site: str = Field(max_length=512)
    city: str = Field(max_length=64)
    country: str = Field(default="Россия", max_length=64)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("title", "city", "country")
    @classmethod
    def check_text(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 2:
            raise ValueError("Слишком коротко")
        return v

    @field_validator("site")
    @classmethod
    def check_site(cls, v: str) -> str:
        v = v.strip()
        try:
            shop_key(v)
        except BadShopUrl as exc:
            raise ValueError(str(exc)) from None
        return v if v.startswith(("http://", "https://")) else f"https://{v}"

    @field_validator("description")
    @classmethod
    def check_description(cls, v: str | None) -> str | None:
        return _clean(v)


class ShopCheckOut(ApiModel):
    """Проверка перед добавлением магазина: тот же сайт уже есть? похожие названия?"""

    site_key: str | None
    site_error: str | None
    same_site: ShopBriefOut | None
    similar: list[ShopBriefOut]

    @classmethod
    def of(cls, c: ShopCheck) -> "ShopCheckOut":
        return cls(
            site_key=c.site_key,
            site_error=c.site_error,
            same_site=ShopBriefOut.of(c.same_site) if c.same_site else None,
            similar=[ShopBriefOut.of(s) for s in c.similar],
        )
