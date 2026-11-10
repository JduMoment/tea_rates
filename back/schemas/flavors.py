from typing import Annotated

from pydantic import AfterValidator

from back.enums.flavor import TASTE_ORDER, Flavor, FlavorGroup, Taste
from back.schemas.base import ApiModel
from back.services.flavors import FlavorProfile, Share

MAX_FLAVORS = 7


def _flavor(v: str) -> Flavor:
    flavor = Flavor.from_slug(v)
    if flavor is None:
        raise ValueError(f"Неизвестный дескриптор: {v}")
    return flavor


def _flavors(v: list[str]) -> list[Flavor]:
    # Повторы убираем, порядок сохраняем
    flavors = list(dict.fromkeys(_flavor(x) for x in v))
    if len(flavors) > MAX_FLAVORS:
        raise ValueError(f"Не больше {MAX_FLAVORS} дескрипторов")
    return flavors


def _tastes(v: list[str]) -> list[Taste]:
    tastes = []
    for x in v:
        taste = Taste.from_slug(x)
        if taste is None:
            raise ValueError(f"Неизвестный вкус: {x}")
        tastes.append(taste)
    return list(dict.fromkeys(tastes))


#: Отмеченные вкусы: ["sweet", "umami"] → [Taste.SWEET, Taste.UMAMI].
TastesIn = Annotated[list[str], AfterValidator(_tastes)]

#: Дескрипторы во входящих данных: ["honey", "citrus"] → [Flavor.HONEY, Flavor.CITRUS].
#: В схеме — список строк (так он и выглядит в /docs), после проверки — список Flavor.
FlavorsIn = Annotated[list[str], AfterValidator(_flavors)]


# ---------- справочник колеса ----------


class TasteOut(ApiModel):
    slug: str
    title: str
    color: str

    @classmethod
    def of(cls, t: Taste) -> "TasteOut":
        return cls(slug=t.slug, title=t.value, color=t.color)


class FlavorOut(ApiModel):
    slug: str
    title: str
    #: slug вкуса: sweet / sour / salty / bitter / umami
    taste: str

    @classmethod
    def of(cls, f: Flavor) -> "FlavorOut":
        return cls(slug=f.slug, title=f.value, taste=f.taste.slug)


class FlavorGroupOut(ApiModel):
    slug: str
    title: str
    color: str
    #: В порядке на колесе по часовой стрелке.
    flavors: list[FlavorOut]

    @classmethod
    def of(cls, g: FlavorGroup) -> "FlavorGroupOut":
        return cls(slug=g.slug, title=g.value, color=g.color, flavors=[FlavorOut.of(f) for f in g.flavors])


class FlavorWheelOut(ApiModel):
    """Всё колесо: вкусы для внутреннего кольца и легенды, группы с дескрипторами — по часовой от «12 часов»."""

    tastes: list[TasteOut]
    groups: list[FlavorGroupOut]

    @classmethod
    def build(cls) -> "FlavorWheelOut":
        return cls(
            tastes=[TasteOut.of(t) for t in TASTE_ORDER],
            groups=[FlavorGroupOut.of(g) for g in FlavorGroup],
        )


# ---------- вкусовой профиль чая ----------


class ShareOut(ApiModel):
    #: slug дескриптора, группы или вкуса
    slug: str
    count: int
    #: Доля отзывов, от 0 до 1
    share: float

    @classmethod
    def of(cls, s: Share) -> "ShareOut":
        return cls(slug=s.item.slug, count=s.count, share=round(s.share, 3))


class FlavorProfileOut(ApiModel):
    """Что слышат в чае: доли отзывов (с дескрипторами), упомянувших дескриптор, группу, вкус."""

    reviews: int
    flavors: list[ShareOut]
    groups: list[ShareOut]
    tastes: list[ShareOut]

    @classmethod
    def of(cls, p: FlavorProfile) -> "FlavorProfileOut":
        return cls(
            reviews=p.reviews,
            flavors=[ShareOut.of(s) for s in p.flavors],
            groups=[ShareOut.of(s) for s in p.groups],
            tastes=[ShareOut.of(s) for s in p.tastes],
        )
