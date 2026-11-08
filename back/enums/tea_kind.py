"""Вид чая и всё, что из него выводится: склонения, цвета, адрес.

В БД хранится только сам вид (Category.name). Формы слова и цвета — здесь, в коде:
так их не нужно заводить руками для каждой записи, и они не разъедутся.
"""

from dataclasses import dataclass
from enum import StrEnum


class TeaKind(StrEnum):
    """Значение — название для людей. В Postgres enum хранится имя члена (GABA), оно не меняется
    при правке подписи."""

    GREEN = "Зелёный"
    WHITE = "Белый"
    OOLONG = "Улун"
    GABA = "Габа"
    RED = "Красный"
    SHU = "Шу пуэр"
    SHENG = "Шен пуэр"
    HERBAL = "Травяной"

    @property
    def slug(self) -> str:
        """Для адресов: /rankings/categories/gaba."""
        return self.name.lower()

    @classmethod
    def from_slug(cls, slug: str) -> "TeaKind | None":
        return cls.__members__.get(slug.upper())

    @property
    def plural(self) -> str:
        """«Габы» — заголовки «У кого брать габы?»."""
        return _LOOKS[self].plural

    @property
    def instrumental(self) -> str:
        """«габами» — фразы «славится габами»."""
        return _LOOKS[self].instrumental

    @property
    def color(self) -> str:
        """Светлый фон плашек и карточек."""
        return _LOOKS[self].color

    @property
    def ink(self) -> str:
        """Тёмный акцент к фону: иконки, полоски рейтинга, подписи на плашке."""
        return _LOOKS[self].ink


@dataclass(frozen=True, slots=True)
class _Look:
    plural: str
    instrumental: str
    color: str
    ink: str


# Русские формы не выводятся по правилу (шу пуэр → шу пуэрами, травяной → травяными сборами),
# поэтому — словарь. Новый член TeaKind без записи здесь упадёт на импорте (проверка ниже).
_LOOKS: dict[TeaKind, _Look] = {
    TeaKind.GREEN: _Look("Зелёные", "зелёными", "#DCEBC4", "#3F6B1F"),
    TeaKind.WHITE: _Look("Белые", "белыми", "#F1ECDD", "#7A6A3A"),
    TeaKind.OOLONG: _Look("Улуны", "улунами", "#FFE3A6", "#8A6212"),
    TeaKind.GABA: _Look("Габы", "габами", "#E4DDF7", "#4A3D78"),
    TeaKind.RED: _Look("Красные", "красными", "#FFD0BE", "#A3401C"),
    TeaKind.SHU: _Look("Шу пуэры", "шу пуэрами", "#F2D5C8", "#7A3F28"),
    TeaKind.SHENG: _Look("Шен пуэры", "шен пуэрами", "#E3EDD9", "#4F6B3A"),
    TeaKind.HERBAL: _Look("Травяные", "травяными сборами", "#DDEFF2", "#2F6670"),
}
assert set(_LOOKS) == set(TeaKind), "У каждого TeaKind должно быть описание в _LOOKS"


#: Порядок по умолчанию: от лёгких к плотным. Страницы с другим порядком заводят свой кортеж.
DEFAULT_ORDER: tuple[TeaKind, ...] = (
    TeaKind.GREEN,
    TeaKind.WHITE,
    TeaKind.OOLONG,
    TeaKind.GABA,
    TeaKind.RED,
    TeaKind.SHU,
    TeaKind.SHENG,
    TeaKind.HERBAL,
)


def in_order[T](items: list[T], kind_of, order: tuple[TeaKind, ...] = DEFAULT_ORDER) -> list[T]:
    """Сортирует что угодно по виду чая в заданном порядке; виды вне order — в конец."""
    position = {kind: i for i, kind in enumerate(order)}
    return sorted(items, key=lambda item: position.get(kind_of(item), len(order)))
