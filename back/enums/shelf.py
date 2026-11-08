from enum import StrEnum


class ShelfStatus(StrEnum):
    """Статус чая в шкафу. Значение — подпись для людей; в API и БД — имя члена."""

    WANT = "Хочу попробовать"
    HAVE = "Есть дома"
    FINISHED = "Закончился"

    @property
    def slug(self) -> str:
        return self.name.lower()

    @classmethod
    def from_slug(cls, slug: str) -> "ShelfStatus | None":
        return cls.__members__.get(slug.upper())
