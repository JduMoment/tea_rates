"""Поиск возможных дублей среди уже заведённых магазинов.

Один сайт дважды завести нельзя (уникальный ключ в БД), но один магазин может прийти с разными
адресами: shop.ru и vk.com/shop. Такие пары ловим по похожим названиям — и смотрим глазами.

    python -m back.shop_duplicates
    docker compose -f deploy/docker-compose.prod.yml exec backend python -m back.shop_duplicates
"""

import asyncio

from sqlalchemy import select

from back.core.db import SessionFactory, engine
from back.models import Shop
from back.services.shops import similar_titles


async def main() -> None:
    async with SessionFactory() as db:
        shops = list(await db.scalars(select(Shop).order_by(Shop.id)))
    await engine.dispose()
    pairs = set()
    for shop in shops:
        for other in similar_titles(shop.title, [s for s in shops if s.id != shop.id]):
            pairs.add(tuple(sorted((shop.id, other.id))))
    if not pairs:
        print(f"Похожих магазинов нет (всего {len(shops)}).")
        return
    by_id = {s.id: s for s in shops}
    print(f"Возможные дубли — {len(pairs)}:")
    for a, b in sorted(pairs):
        for s in (by_id[a], by_id[b]):
            print(f"  #{s.id} {s.title} · {s.site_key} · {s.city} · /shops/{s.name}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
