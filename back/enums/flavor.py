"""Колесо ароматов: группа → дескриптор. Базовый вкус (сладкий, умами…) автор отзыва отмечает сам.

Середина между нашим первым колесом (подробным, в духе кофейного) и колесом Art of Tea:
групп и нот меньше, названия житейские («малина, клубника», а не «красные ягоды»),
без нот, которые в чае не различить (бергамот против лайма, краб, сера).

Пользователь в отзыве выбирает дескрипторы (Flavor) на колесе и отдельно — базовые вкусы (Taste).
Группа дескриптора выводится отсюда: справочник целиком живёт в коде, в БД хранятся лишь выбранные Flavor.

У дескриптора есть и вкус — по нему выводится вкус отзыва, где автор вкус сам не отметил
(старые отзывы, до отдельного выбора вкуса). Вкус задаётся у группы по умолчанию,
отдельные дескрипторы его переопределяют (во «фруктовом» есть и сладкое, и кислое).

Порядок членов FlavorGroup и порядок дескрипторов в _WHEEL — это порядок на колесе
по часовой стрелке от «12 часов».
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum


class _Slugged(StrEnum):
    """Значение — подпись для людей; в API — slug (имя члена в нижнем регистре)."""

    @property
    def slug(self) -> str:
        return self.name.lower()

    @classmethod
    def from_slug(cls, slug: str):
        return cls.__members__.get(slug.upper())


class Taste(_Slugged):
    SWEET = "Сладкий"
    SOUR = "Кислый"
    SALTY = "Солёный"
    BITTER = "Горький"
    UMAMI = "Умами"

    @property
    def color(self) -> str:
        return _TASTE_COLORS[self]


class FlavorGroup(_Slugged):
    FLOWERS = "Цветочный"
    HERBAL = "Травянистый"
    VEGETABLE = "Овощной"
    MINERAL = "Минеральный"
    EARTHY = "Почвенный"
    WOODY = "Древесный, дымный"
    SPICY = "Пряный"
    ROASTED = "Жареный"
    NUTTY = "Орехи, семечки"
    CONFECTIONERY = "Кондитерский"
    DRIED_FRUIT = "Сухофрукты, варенье"
    BERRY = "Ягодный"
    FRUIT = "Фруктовый"

    @property
    def color(self) -> str:
        return _WHEEL[self].color

    @property
    def flavors(self) -> tuple["Flavor", ...]:
        """Дескрипторы группы в порядке на колесе."""
        return _WHEEL[self].flavors


class Flavor(_Slugged):
    """Конкретный дескриптор. В БД хранится имя члена (HONEY) — его не менять, подпись можно.

    Удалили член — перенесите старые отзывы на ближайший оставшийся, иначе такие строки
    не прочитаются из БД.
    """

    # Цветочный
    JASMINE = "жасмин"
    ROSE = "роза"
    LINDEN = "липа"
    ORCHID = "орхидея"
    MEADOW_FLOWERS = "луговые цветы"
    OSMANTHUS = "османтус"
    # Травянистый
    CUT_GRASS = "свежая трава"
    HAY = "сено"
    MINT = "мята"
    MENTHOL = "ментол"
    HERBS = "пряные травы"
    # Овощной
    SPINACH = "шпинат"
    PEA = "зелёный горошек"
    ASPARAGUS = "спаржа"
    GREEN_BEANS = "стручковая фасоль"
    PUMPKIN = "тыква"
    SWEET_POTATO = "батат"
    # Морской, минеральный
    SEAWEED = "водоросли"
    SALT = "морская соль"
    WET_STONE = "мокрый камень"
    # Почвенный
    EARTH = "земля"
    FOREST_FLOOR = "прелая листва"
    MUSHROOM = "грибы"
    LEATHER = "кожа"
    TOBACCO = "табак"
    # Древесный, дымный
    DRY_WOOD = "сухое дерево"
    CONIFER = "хвоя"
    RESIN = "смола"
    CAMPHOR = "камфора"
    SMOKE = "дым"
    SMOKED = "копчёности"
    # Пряный
    CINNAMON = "корица"
    GINGER = "имбирь"
    CLOVE = "гвоздика"
    ANISE = "анис"
    PEPPER = "перец"
    # Жареный
    COCOA = "какао"
    CHOCOLATE = "шоколад"
    COFFEE = "кофе"
    ROASTED_GRAIN = "жареное зерно"
    ROASTED_RICE = "жареный рис"
    ROASTED_BEANS = "жареные бобы, соя"
    # Ореховый
    HAZELNUT = "лесной орех"
    ALMOND = "миндаль"
    WALNUT = "грецкий орех"
    CHESTNUT = "каштан"
    SEEDS = "жареные семечки"
    SESAME = "кунжут"
    # Кондитерский
    HONEY = "мёд"
    CARAMEL = "карамель"
    VANILLA = "ваниль"
    CREAM = "сливки"
    BREAD = "хлеб, злаки"
    COOKIE = "печенье"
    MALT = "солод"
    # Сухофрукты, варенье
    RAISIN = "изюм"
    DRIED_APRICOT = "курага"
    PRUNE = "чернослив"
    FIG = "инжир"
    DATE = "финик"
    JAM = "варенье"
    # Ягодный
    RED_BERRIES = "малина, клубника"
    BLACKBERRY = "ежевика"
    DARK_BERRIES = "смородина, черника"
    SOUR_BERRIES = "клюква, брусника"
    CHERRY = "вишня"
    ROSEHIP = "шиповник"
    SEA_BUCKTHORN = "облепиха"
    # Фруктовый
    APPLE = "яблоко"
    PEAR = "груша"
    PEACH = "персик, абрикос"
    PLUM = "слива"
    GRAPE = "виноград"
    MUSCAT = "мускат"
    MELON = "дыня"
    CITRUS = "цитрус"
    LYCHEE = "личи"
    TROPICAL = "тропические фрукты"

    @property
    def group(self) -> FlavorGroup:
        return _GROUP_OF[self]

    @property
    def taste(self) -> Taste:
        return _TASTE_OF[self]


_TASTE_COLORS: dict[Taste, str] = {
    Taste.SWEET: "#EF4045",
    Taste.SOUR: "#12B848",
    Taste.SALTY: "#2E5BFF",
    Taste.BITTER: "#424242",
    Taste.UMAMI: "#8E5CC4",
}
assert set(_TASTE_COLORS) == set(Taste), "У каждого Taste должен быть цвет"

#: Порядок вкусов в легенде.
TASTE_ORDER: tuple[Taste, ...] = tuple(Taste)


@dataclass(frozen=True, slots=True)
class _Group:
    color: str
    #: Вкус дескрипторов группы, если он не переопределён в overrides.
    taste: Taste
    flavors: tuple[Flavor, ...]
    overrides: Mapping[Flavor, Taste] = field(default_factory=dict)


#: Цвета групп — пастель в тон сайту: на колесе их много, насыщенные спорили друг с другом.
#: Порядок групп — по кругу от светлого к тёмному и обратно: цветы → травы → овощи → море →
#: земля → дерево → пряности → обжарка → орехи → сладкое → сухофрукты → ягоды → фрукты → цветы.
_WHEEL: dict[FlavorGroup, _Group] = {
    FlavorGroup.FLOWERS: _Group(
        "#F2B8C6",
        Taste.SWEET,
        (Flavor.JASMINE, Flavor.ROSE, Flavor.LINDEN, Flavor.ORCHID, Flavor.MEADOW_FLOWERS, Flavor.OSMANTHUS),
    ),
    FlavorGroup.HERBAL: _Group(
        "#BCD9A0",
        Taste.SWEET,
        (Flavor.CUT_GRASS, Flavor.HAY, Flavor.MINT, Flavor.MENTHOL, Flavor.HERBS),
        {Flavor.HERBS: Taste.BITTER},
    ),
    FlavorGroup.VEGETABLE: _Group(
        "#D6D59A",
        Taste.UMAMI,
        (Flavor.SPINACH, Flavor.PEA, Flavor.ASPARAGUS, Flavor.GREEN_BEANS, Flavor.PUMPKIN, Flavor.SWEET_POTATO),
        {Flavor.PUMPKIN: Taste.SWEET, Flavor.SWEET_POTATO: Taste.SWEET},
    ),
    FlavorGroup.MINERAL: _Group(
        "#A9D3CC",
        Taste.SALTY,
        (Flavor.SEAWEED, Flavor.SALT, Flavor.WET_STONE),
        {Flavor.SEAWEED: Taste.UMAMI},
    ),
    FlavorGroup.EARTHY: _Group(
        "#B9A99A",
        Taste.BITTER,
        (Flavor.EARTH, Flavor.FOREST_FLOOR, Flavor.MUSHROOM, Flavor.LEATHER, Flavor.TOBACCO),
        {Flavor.MUSHROOM: Taste.UMAMI},
    ),
    FlavorGroup.WOODY: _Group(
        "#CFAE8F",
        Taste.BITTER,
        (Flavor.DRY_WOOD, Flavor.CONIFER, Flavor.RESIN, Flavor.CAMPHOR, Flavor.SMOKE, Flavor.SMOKED),
    ),
    FlavorGroup.SPICY: _Group(
        "#E9AF8E",
        Taste.BITTER,
        (Flavor.CINNAMON, Flavor.GINGER, Flavor.CLOVE, Flavor.ANISE, Flavor.PEPPER),
        {Flavor.CINNAMON: Taste.SWEET, Flavor.ANISE: Taste.SWEET},
    ),
    FlavorGroup.ROASTED: _Group(
        "#C9A592",
        Taste.BITTER,
        (
            Flavor.COCOA,
            Flavor.CHOCOLATE,
            Flavor.COFFEE,
            Flavor.ROASTED_GRAIN,
            Flavor.ROASTED_RICE,
            Flavor.ROASTED_BEANS,
        ),
        {Flavor.CHOCOLATE: Taste.SWEET, Flavor.ROASTED_RICE: Taste.SWEET},
    ),
    FlavorGroup.NUTTY: _Group(
        "#E2C29A",
        Taste.SWEET,
        (Flavor.HAZELNUT, Flavor.ALMOND, Flavor.WALNUT, Flavor.CHESTNUT, Flavor.SEEDS, Flavor.SESAME),
        {Flavor.WALNUT: Taste.BITTER},
    ),
    FlavorGroup.CONFECTIONERY: _Group(
        "#F0D3A8",
        Taste.SWEET,
        (Flavor.HONEY, Flavor.CARAMEL, Flavor.VANILLA, Flavor.CREAM, Flavor.BREAD, Flavor.COOKIE, Flavor.MALT),
    ),
    FlavorGroup.DRIED_FRUIT: _Group(
        "#D9A3A0",
        Taste.SWEET,
        (Flavor.RAISIN, Flavor.DRIED_APRICOT, Flavor.PRUNE, Flavor.FIG, Flavor.DATE, Flavor.JAM),
    ),
    FlavorGroup.BERRY: _Group(
        "#E7A3B4",
        Taste.SWEET,
        (
            Flavor.RED_BERRIES,
            Flavor.BLACKBERRY,
            Flavor.DARK_BERRIES,
            Flavor.SOUR_BERRIES,
            Flavor.CHERRY,
            Flavor.ROSEHIP,
            Flavor.SEA_BUCKTHORN,
        ),
        {Flavor.SOUR_BERRIES: Taste.SOUR, Flavor.CHERRY: Taste.SOUR, Flavor.SEA_BUCKTHORN: Taste.SOUR},
    ),
    FlavorGroup.FRUIT: _Group(
        "#F5BE9A",
        Taste.SWEET,
        (
            Flavor.APPLE,
            Flavor.PEAR,
            Flavor.PEACH,
            Flavor.PLUM,
            Flavor.GRAPE,
            Flavor.MUSCAT,
            Flavor.MELON,
            Flavor.CITRUS,
            Flavor.LYCHEE,
            Flavor.TROPICAL,
        ),
        {Flavor.CITRUS: Taste.SOUR},
    ),
}

_GROUP_OF: dict[Flavor, FlavorGroup] = {f: g for g, spec in _WHEEL.items() for f in spec.flavors}
_TASTE_OF: dict[Flavor, Taste] = {
    f: spec.overrides.get(f, spec.taste) for spec in _WHEEL.values() for f in spec.flavors
}

# Проверки на импорте: новый член enum без места на колесе — сразу ошибка, а не тихая дыра
assert list(_WHEEL) == list(FlavorGroup), "_WHEEL должен описывать все FlavorGroup в их порядке"
assert sum(len(s.flavors) for s in _WHEEL.values()) == len(_GROUP_OF), "Дескриптор встречается в двух группах"
assert set(_GROUP_OF) == set(Flavor), "Каждый Flavor должен быть ровно в одной группе _WHEEL"
assert all(set(s.overrides) <= set(s.flavors) for s in _WHEEL.values()), "overrides — только для своих дескрипторов"
