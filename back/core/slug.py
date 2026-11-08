"""Системные имена (slug) из русских названий: «Габа Алишань» → «gaba-alishan»."""

import re

_TRANSLIT = str.maketrans(
    {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z",
        "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
        "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
)  # fmt: skip


def slugify(title: str, max_length: int = 64) -> str:
    """Латиница, цифры и дефисы. Пустое название даёт «tea» — чтобы имя не было пустым."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower().translate(_TRANSLIT)).strip("-")
    return slug[:max_length].rstrip("-") or "tea"


def unique_slug(title: str, taken: set[str], max_length: int = 64) -> str:
    """slugify + числовой суффикс, если имя занято: gaba-alishan, gaba-alishan-2, …"""
    base = slugify(title, max_length - 4)
    slug, n = base, 1
    while slug in taken:
        n += 1
        slug = f"{base}-{n}"
    return slug
