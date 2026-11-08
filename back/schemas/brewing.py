from back.schemas.base import ApiModel
from back.services.brewing import Brewed, Brewing, Typical


class TypicalOut(ApiModel):
    """Типичные параметры вида чая: [от, до]."""

    water: tuple[int, int]
    grams_per_100: tuple[float, float]
    infusions: tuple[int, int]

    @classmethod
    def of(cls, t: Typical) -> "TypicalOut":
        return cls(water=t.water, grams_per_100=t.grams_per_100, infusions=t.infusions)


class BrewedOut(ApiModel):
    """Медианы по записям дневников."""

    entries: int
    people: int
    water: int
    grams: float
    infusions: int
    volume: int | None
    grams_per_100: float | None

    @classmethod
    def of(cls, b: Brewed) -> "BrewedOut":
        return cls(
            entries=b.entries,
            people=b.people,
            water=b.water,
            grams=b.grams,
            infusions=b.infusions,
            volume=b.volume,
            grams_per_100=b.grams_per_100,
        )


class BrewingOut(ApiModel):
    """Как заваривают чай. community/liked — null, пока записей в дневниках мало: тогда смотрите typical."""

    #: «Зелёные» — для подписи «типично для зелёных»
    category: str
    typical: TypicalOut
    community: BrewedOut | None
    liked: BrewedOut | None

    @classmethod
    def of(cls, b: Brewing) -> "BrewingOut":
        return cls(
            category=b.kind.plural,
            typical=TypicalOut.of(b.typical),
            community=BrewedOut.of(b.community) if b.community else None,
            liked=BrewedOut.of(b.liked) if b.liked else None,
        )
