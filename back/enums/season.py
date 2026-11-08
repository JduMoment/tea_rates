from enum import StrEnum


class Season(StrEnum):
    """Сезон сбора чая. Значение — подпись для людей; в Postgres enum хранится имя члена (SPRING)."""

    SPRING = "Весна"
    SUMMER = "Лето"
    AUTUMN = "Осень"
    WINTER = "Зима"

    @property
    def slug(self) -> str:
        """Для API и фильтров: spring."""
        return self.name.lower()

    @classmethod
    def from_slug(cls, slug: str) -> "Season | None":
        return cls.__members__.get(slug.upper())
