"""Превью ссылок: мета-теги Open Graph для страниц и картинка 1200×630 для карточки в мессенджерах.

Telegram, ВКонтакте, WhatsApp не выполняют JavaScript — поэтому заголовок, описание и картинку
сервер вставляет прямо в index.html (см. views/frontend.py), а картинку рисует здесь же, Pillow.
"""

import math
import re
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.ext.asyncio import AsyncSession

from back.core.config import PUBLIC_URL
from back.enums.tea_kind import TeaKind
from back.services.catalog import CatalogService
from back.services.errors import NotFoundError
from back.services.flavors import FlavorStatsService
from back.services.social import SocialService

SITE = "5 листов"
TAGLINE = "Один чай\u00a0— разные чашки. Сравнивайте чай из разных магазинов и доверяйте тем, кто пьёт давно"
FONTS = Path(__file__).resolve().parents[1] / "assets" / "fonts"
INK = "#22301a"
BG = "#fbf8f0"
ACCENT_SOFT = "#dcebc4"


@dataclass(frozen=True, slots=True)
class Preview:
    title: str
    description: str
    #: Адрес картинки относительно сайта: /og/teas/12.png
    image: str
    #: Для картинки: надпись над заголовком, оценка, отзывы, ноты.
    eyebrow: str = ""
    score: float | None = None
    reviews: int = 0
    notes: tuple[tuple[str, str], ...] = ()  # (подпись, цвет)
    color: str = ACCENT_SOFT


def _score(v: float) -> str:
    return f"{v:.1f}".replace(".", ",")


def _plural(n: int, one: str, few: str, many: str) -> str:
    m10, m100 = n % 10, n % 100
    if m10 == 1 and m100 != 11:
        return one
    if 2 <= m10 <= 4 and not 12 <= m100 <= 14:
        return few
    return many


DEFAULT = Preview(title=f"{SITE} — рейтинг чаёв по магазинам", description=TAGLINE, image="/og/default.png")

#: Разделы без своих данных: заголовок и описание
STATIC: dict[str, tuple[str, str]] = {
    "/teas": ("Все чаи", "Каталог чаёв: где какой продаётся, почём и что о нём пишут. Поиск по нотам вкуса."),
    "/shops": ("Магазины чая", "Чайные магазины и их оценки по отзывам — в каждом виде чая отдельно."),
    "/privacy": ("Конфиденциальность", "Какие данные собирает сайт «5 листов», зачем и как от этого отказаться."),
    "/rankings": ("Рейтинги", "Лучшие чаи и магазины по отзывам: топ чаёв, лидеры по видам чая, рейтинг магазинов."),
}


class PreviewService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def for_path(self, path: str) -> Preview:
        """Превью для адреса страницы фронта. Неизвестное или несуществующее — общее превью сайта."""
        try:
            if m := re.fullmatch(r"/teas/(\d+)", path):
                return await self.tea(int(m[1]))
            if m := re.fullmatch(r"/shops/([\w-]+)", path):
                return await self.shop(m[1])
            if m := re.fullmatch(r"/users/(\d+)", path):
                return await self.author(int(m[1]))
        except NotFoundError:
            return DEFAULT
        for prefix, (title, description) in STATIC.items():
            if path == prefix or path.startswith(prefix + "/"):
                return Preview(title=f"{title} — {SITE}", description=description, image="/og/default.png")
        return DEFAULT

    async def tea(self, tea_id: int) -> Preview:
        catalog = CatalogService(self.db)
        tea = await catalog.get_tea(tea_id)
        [rated] = await catalog.rate([tea])
        profile = await FlavorStatsService(self.db).for_tea(tea_id)
        kind: TeaKind = tea.category.name
        notes = tuple((s.item.value, s.item.group.color) for s in profile.flavors[:4])
        parts = [kind.value]
        if rated.score.reviews:
            n = rated.score.reviews
            parts.append(f"{_score(rated.score.shown)} из 5 по {n} {_plural(n, 'отзыву', 'отзывам', 'отзывам')}")
        shops = len(tea.offers)
        if shops:
            parts.append(f"продаётся в {shops} {_plural(shops, 'магазине', 'магазинах', 'магазинах')}")
        description = " · ".join(parts) + "."
        if notes:
            description += " Чаще всего слышат: " + " · ".join(n for n, _ in notes) + "."
        return Preview(
            title=f"{tea.title} — {SITE}",
            description=description,
            image=f"/og/teas/{tea_id}.png",
            eyebrow=kind.value,
            score=rated.score.shown if rated.score.reviews else None,
            reviews=rated.score.reviews,
            notes=notes,
            color=kind.color,
        )

    async def shop(self, name: str) -> Preview:
        details = await CatalogService(self.db).shop(name)
        s, score = details.summary.shop, details.summary.score
        kinds = {c.id: c.name for c in await CatalogService(self.db).categories()}
        famous = [kinds[sp.category_id].instrumental for sp in details.summary.specialties if sp.category_id in kinds]
        teas = details.summary.tea_count
        parts = [f"{s.city}, {s.country}", f"{teas} {_plural(teas, 'чай', 'чая', 'чаёв')}"]
        if score.reviews:
            parts.append(
                f"{_score(score.shown)} из 5 по {score.reviews} {_plural(score.reviews, 'отзыву', 'отзывам', 'отзывам')}"
            )
        description = " · ".join(parts) + "."
        if famous:
            description += f" Славится {' и '.join(famous[:2])}."
        return Preview(
            title=f"{s.title} — {SITE}",
            description=description,
            image=f"/og/shops/{s.name}.png",
            eyebrow=f"Магазин чая · {s.city}",
            score=score.shown if score.reviews else None,
            reviews=score.reviews,
        )

    async def author(self, user_id: int) -> Preview:
        p = await SocialService(self.db).profile(user_id, None)
        flavors = await FlavorStatsService(self.db).for_user(user_id)
        notes = tuple((s.item.value, s.item.group.color) for s in flavors.flavors[:4])
        description = (
            f"{p.reviews} {_plural(p.reviews, 'отзыв', 'отзыва', 'отзывов')} о "
            f"{p.teas} {_plural(p.teas, 'чае', 'чаях', 'чаях')} на сайте «{SITE}»."
        )
        if notes:
            description += " Любимые ноты: " + " · ".join(n for n, _ in notes) + "."
        return Preview(
            title=f"{p.user.name} — {SITE}",
            description=description,
            image=f"/og/users/{user_id}.png",
            eyebrow="Автор отзывов",
            reviews=p.reviews,
            notes=notes,
            color="#fde3a7",
        )


# ---------- картинка ----------

W, H = 1200, 630
PAD = 72


def _font(name: str, size: int, weight: str | None = None) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(FONTS / name), size)
    if weight:
        font.set_variation_by_name(weight)
    return font


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int, lines: int) -> list[str]:
    """Перенос по словам; не влезло в lines строк — последнюю обрезаем с многоточием."""
    out: list[str] = []
    words = text.split()
    line = ""
    for w in words:
        trial = f"{line} {w}".strip()
        if draw.textlength(trial, font=font) <= width:
            line = trial
        else:
            out.append(line)
            line = w
    out.append(line)
    if len(out) > lines:
        out = out[:lines]
        while draw.textlength(out[-1] + "…", font=font) > width and " " in out[-1]:
            out[-1] = out[-1].rsplit(" ", 1)[0]
        out[-1] += "…"
    return out


def _text_on(hex_color: str) -> str:
    n = int(hex_color.lstrip("#"), 16)
    r, g, b = (n >> 16) & 255, (n >> 8) & 255, n & 255
    return INK if 0.299 * r + 0.587 * g + 0.114 * b > 150 else "#ffffff"


def _bezier(p0, p1, p2, p3, steps: int = 24) -> list[tuple[float, float]]:
    return [
        (
            (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t**2 * p2[0] + t**3 * p3[0],
            (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t**2 * p2[1] + t**3 * p3[1],
        )
        for t in (i / steps for i in range(steps + 1))
    ]


#: Лепесток розетки в поле 64×64 относительно центра знака — как в front/public/favicon.svg.
_PETAL = _bezier((0, -3), (-8.1, -9.5), (-8.1, -20.3), (0, -26.8)) + _bezier(
    (0, -26.8), (8.1, -20.3), (8.1, -9.5), (0, -3)
)


def mark(size: int, plate: bool = True) -> Image.Image:
    """Знак сайта — розетка из пяти листьев (тот же рисунок, что favicon.svg), RGBA size×size.
    Рисуем в 4 раза крупнее и уменьшаем — Pillow не сглаживает края фигур."""
    k = size * 4 / 64
    img = Image.new("RGBA", (size * 4, size * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if plate:
        d.rounded_rectangle((0, 0, size * 4 - 1, size * 4 - 1), radius=int(16 * k), fill="#dcebc4")
    cx, cy = 32 * k, 33 * k
    for i in range(5):
        a = math.radians(72 * i)
        cos, sin = math.cos(a), math.sin(a)
        at = [(cx + (x * cos - y * sin) * k, cy + (x * sin + y * cos) * k) for x, y in [*_PETAL, (0, -6), (0, -20)]]
        d.polygon(at[:-2], fill="#3f6b1f")
        d.line(at[-2:], fill="#dcebc4", width=max(1, round(1.6 * k)))
    r = 3.4 * k
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill="#ffe3a6")
    return img.resize((size, size), Image.Resampling.LANCZOS)


def render(p: Preview) -> bytes:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # Цветная плашка во весь кадр с полями — как hero на сайте
    d.rounded_rectangle((24, 24, W - 24, H - 24), radius=48, fill=p.color)

    logo = mark(64)
    img.paste(logo, (PAD, PAD - 18), logo)
    small = _font("Manrope-Variable.ttf", 26, "SemiBold")
    site = PUBLIC_URL.split("://")[-1]
    d.text((W - PAD, PAD + 6), site, font=small, fill=INK, anchor="ra")

    y = 170
    if p.eyebrow:
        d.text((PAD, y), p.eyebrow, font=_font("Manrope-Variable.ttf", 30, "Bold"), fill=INK)
        y += 52
    # Название сайта уже в логотипе: «5 листов — рейтинг…» → «Рейтинг…», «Габа — 5 листов» → «Габа»
    title = p.title.removesuffix(f" — {SITE}").removeprefix(f"{SITE} — ")
    title = title[:1].upper() + title[1:]
    size = 92 if len(title) <= 22 else 76 if len(title) <= 40 else 64
    tfont = _font("YesevaOne-Regular.ttf", size)
    for line in _wrap(d, title, tfont, W - 2 * PAD, 2):
        d.text((PAD, y), line, font=tfont, fill=INK)
        y += int(size * 1.12)

    # Низ: оценка-наклейка, число отзывов, ноты
    base = H - PAD - 56
    x = PAD
    if p.score is not None:
        sfont = _font("Manrope-Variable.ttf", 40, "ExtraBold")
        label = _score(p.score)
        tw = d.textlength(label, font=sfont)
        d.rounded_rectangle((x, base, x + tw + 40, base + 64), radius=20, fill="#ffffff")
        d.text((x + 20, base + 32), label, font=sfont, fill=INK, anchor="lm")
        x += tw + 60
    if p.reviews:
        rfont = _font("Manrope-Variable.ttf", 28, "SemiBold")
        label = f"{p.reviews} {_plural(p.reviews, 'отзыв', 'отзыва', 'отзывов')}"
        d.text((x, base + 32), label, font=rfont, fill=INK, anchor="lm")
        x += d.textlength(label, font=rfont) + 36
    nfont = _font("Manrope-Variable.ttf", 26, "Bold")
    for note, color in p.notes:
        tw = d.textlength(note, font=nfont)
        if x + tw + 36 > W - PAD:
            break
        d.rounded_rectangle((x, base + 8, x + tw + 32, base + 56), radius=24, fill=color)
        d.text((x + 16, base + 32), note, font=nfont, fill=_text_on(color), anchor="lm")
        x += tw + 44
    if p is DEFAULT or (not p.notes and p.score is None and not p.reviews):
        dfont = _font("Manrope-Variable.ttf", 32, "Medium")
        for i, line in enumerate(_wrap(d, TAGLINE, dfont, W - 2 * PAD, 2)):
            d.text((PAD, base - 40 + i * 44), line, font=dfont, fill=INK)

    out = BytesIO()
    img.save(out, "PNG", optimize=True)
    return out.getvalue()


# Картинки дорого рисовать на каждый запрос краулера — держим в памяти 10 минут
_CACHE: dict[str, tuple[float, bytes]] = {}
CACHE_TTL = 600
CACHE_MAX = 500


def cached_render(key: str, p: Preview) -> bytes:
    now = time.monotonic()
    hit = _CACHE.get(key)
    if hit and hit[0] > now:
        return hit[1]
    data = render(p)
    if len(_CACHE) >= CACHE_MAX:
        _CACHE.clear()
    _CACHE[key] = (now + CACHE_TTL, data)
    return data
