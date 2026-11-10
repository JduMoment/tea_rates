"""Ключ сайта магазина — по нему ловим дубли.

«https://www.Shop.ru/catalog?x=1», «shop.ru» и «http://shop.ru/» — один и тот же магазин: ключ «shop.ru».
Кириллические домены приводятся к punycode: «чай.рф» и «xn--80ajc.xn--p1ai» совпадут.

На площадках (ВКонтакте, Telegram, маркетплейсы) на одном домене живут тысячи продавцов,
поэтому там к домену добавляется страница продавца: «vk.com/teashop», «ozon.ru/seller/chay-123».
"""

import re
from urllib.parse import urlsplit


class BadShopUrl(ValueError):
    pass


#: Площадки, где магазин — это страница на общем домене.
PLATFORMS = {
    "vk.com",
    "vk.ru",
    "m.vk.com",
    "t.me",
    "telegram.me",
    "instagram.com",
    "ozon.ru",
    "wildberries.ru",
    "wb.ru",
    "avito.ru",
    "market.yandex.ru",
    "megamarket.ru",
    "taplink.cc",
    "taplink.ws",
}
#: На этих площадках первый сегмент пути — тип страницы, а продавец — второй: ozon.ru/seller/<имя>.
SECTION_PREFIXES = {"seller", "brand", "shop", "store", "user", "profile", "business", "s", "brands"}
#: Мобильные версии — тот же сайт.
_LEGACY_MOBILE = {"m.vk.com": "vk.com"}


def shop_key(url: str) -> str:
    """Нормализованный ключ сайта магазина. BadShopUrl — если это не похоже на адрес сайта."""
    raw = url.strip()
    if not raw:
        raise BadShopUrl("Укажите сайт магазина")
    if not re.match(r"^[a-z][a-z0-9+.-]*://", raw, re.IGNORECASE):
        raw = "https://" + raw
    parts = urlsplit(raw)
    if parts.scheme.lower() not in ("http", "https"):
        raise BadShopUrl("Нужна ссылка на сайт: https://…")
    host = (parts.hostname or "").rstrip(".").lower()
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise BadShopUrl("Не получается разобрать адрес сайта") from exc
    host = host.removeprefix("www.")
    host = _LEGACY_MOBILE.get(host, host)
    if "." not in host or not re.fullmatch(r"[a-z0-9.-]+", host):
        raise BadShopUrl("Это не похоже на адрес сайта")
    if host not in PLATFORMS:
        return host
    segments = [s.lower() for s in parts.path.split("/") if s]
    if not segments:
        raise BadShopUrl(f"Укажите страницу магазина на {host}, а не главную площадки")
    take = 2 if segments[0] in SECTION_PREFIXES and len(segments) > 1 else 1
    return f"{host}/{'/'.join(segments[:take])}"
