"""Заполняет БД демо-данными из back/fixtures/catalog.json (те же, что были в моках фронта).

    python -m back.seed [--author EMAIL]
    docker compose -f deploy/docker-compose.yml exec backend python -m back.seed --author me@example.com

--author — почта существующего пользователя: он станет автором (author_id) всех чаёв и предложений.

Таблицы должны уже существовать. Запуск повторяемый: магазины обновляются по name,
чаи — по виду и title, предложения — по чаю и магазину, пользователи — по почте;
цены из фикстуры становятся стартовыми ценами предложений; у отзыва с полем purchase — своя покупка
(цена, вес, партия), у остальных каждому второму отзыву цена предложения становится ценой покупки;
отзывы не дублируются (чай × магазин × автор).
Ключи вида «t1», «u1» в фикстуре — только для ссылок внутри неё, в БД не попадают.
"""

import argparse
import asyncio
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from back.core.db import SessionFactory, engine
from back.core.security import NO_PASSWORD
from back.core.slug import unique_slug
from back.enums.flavor import Flavor
from back.enums.season import Season
from back.enums.tea_kind import TeaKind
from back.models import Category, DiaryEntry, Offer, Review, Shop, Tea, User
from back.models.review import Infusion, Purchase

FIXTURE = Path(__file__).parent / "fixtures" / "catalog.json"


class CatalogSeeder:
    def __init__(self, db: AsyncSession, data: dict, author_id: int | None = None) -> None:
        self.db = db
        self.data = data
        self.author_id = author_id  # автор чаёв и предложений
        self.categories: dict[TeaKind, int] = {}  # вид → id в БД
        self.shops: dict[str, int] = {}  # name магазина → id в БД
        self.teas: dict[str, int] = {}  # ключ из фикстуры («t1») → id в БД
        self.users: dict[str, int] = {}  # «u1» → id в БД

    async def run(self) -> dict[str, int]:
        stats = {
            "categories": await self.load_categories(),
            "shops": await self.load_shops(),
            "teas": await self.load_teas(),
            "offers": await self.load_offers(),
            "users": await self.load_users(),
            "reviews": await self.load_reviews(),
            "diary": await self.load_diary(),
        }
        await self.db.commit()
        return stats

    async def load_categories(self) -> int:
        """По записи на каждый TeaKind. Список видов задаёт enum, а не фикстура."""
        existing = {c.name: c.id for c in await self.db.scalars(select(Category))}
        missing = [Category(name=kind) for kind in TeaKind if kind not in existing]
        self.db.add_all(missing)
        await self.db.flush()
        self.categories = existing | {c.name: c.id for c in missing}
        return len(missing)

    async def load_shops(self) -> int:
        existing = {s.name: s for s in await self.db.scalars(select(Shop))}
        for fields in self.data["shops"]:
            shop = existing.get(fields["name"])
            if shop:
                for attr, value in fields.items():
                    setattr(shop, attr, value)
            else:
                shop = Shop(**fields)
                self.db.add(shop)
            await self.db.flush()
            self.shops[shop.name] = shop.id
        return len(self.data["shops"])

    async def load_teas(self) -> int:
        existing = {(t.category_id, t.title.lower()): t for t in await self.db.scalars(select(Tea))}
        names = {t.name for t in existing.values()}
        for t in self.data["teas"]:
            kind = TeaKind.from_slug(t["category"])
            if kind is None:
                raise ValueError(f"{t['key']}: неизвестный вид чая")
            fields = {
                "category_id": self.categories[kind],
                "title": t["title"],
                "region": t["region"],
                "description": t["description"],
                "author_id": self.author_id,
            }
            tea = existing.get((fields["category_id"], t["title"].lower()))
            if tea:
                for attr, value in fields.items():
                    setattr(tea, attr, value)
            else:
                tea = Tea(name=unique_slug(t["title"], names), **fields)
                names.add(tea.name)
                self.db.add(tea)
            await self.db.flush()
            self.teas[t["key"]] = tea.id
        return len(self.teas)

    async def load_offers(self) -> int:
        existing = {(o.tea_id, o.shop_id): o for o in await self.db.scalars(select(Offer))}
        count = 0
        for t in self.data["teas"]:
            for o in t["offers"]:
                key = (self.teas[t["key"]], self.shops[o["shop"]])
                # Цена из фикстуры — стартовая: её покажут, пока нет отзывов с ценой
                fields = {
                    "start_price": o["price"],
                    "start_weight": o["weight"],
                    "url": o.get("url"),
                    "author_id": self.author_id,
                }
                if offer := existing.get(key):
                    for attr, value in fields.items():
                        setattr(offer, attr, value)
                else:
                    self.db.add(Offer(tea_id=key[0], shop_id=key[1], **fields))
                count += 1
        await self.db.flush()
        return count

    async def load_users(self) -> int:
        created = 0
        for u in self.data["users"]:
            user = await self.db.scalar(select(User).where(User.email == u["email"]))
            if not user:
                user = User(
                    name=u["name"],
                    email=u["email"],
                    password_hash=NO_PASSWORD,  # демо-авторы отзывов войти не могут
                    created_at=datetime.fromisoformat(u["joined"]).replace(tzinfo=UTC),
                )
                self.db.add(user)
                await self.db.flush()
                created += 1
            self.users[u["key"]] = user.id
        return created

    async def load_reviews(self) -> int:
        existing = {
            (r.tea_id, r.shop_id, r.user_id): r
            for r in await self.db.scalars(select(Review).where(Review.user_id.in_(self.users.values())))
        }
        # Цена и партия в фикстуре заданы у предложений; каждому второму отзыву даём их как сведения
        # о покупке — так на страницах видны оба источника цены: из отзыва и стартовая.
        offers = {(t["key"], o["shop"]): o for t in self.data["teas"] for o in t["offers"]}
        created = 0
        for i, r in enumerate(self.data["reviews"]):
            key = (self.teas[r["tea"]], self.shops[r["shop"]], self.users[r["user"]])
            infusion = Infusion(**r["infusion"]) if r.get("infusion") else Infusion()
            if key in existing:
                # Шкалы настоя появились позже отзывов — дописываем их уже залитым демо-отзывам
                old = existing[key]
                if r.get("infusion") and old.body is None and old.strength is None and old.aftertaste is None:
                    old.set_infusion(infusion)
                continue
            flavors = [Flavor.from_slug(f) for f in r["flavors"]]
            if None in flavors:
                raise ValueError(f"Отзыв на {r['tea']}: неизвестный дескриптор в {r['flavors']}")
            review = Review(
                tea_id=key[0],
                shop_id=key[1],
                user_id=key[2],
                rating=r["rating"],
                text=r["text"],
                flavors=flavors,
                created_at=datetime.fromisoformat(r["createdAt"]),
            )
            if "purchase" in r:
                # Сгенерированные отзывы несут свою покупку (или null) — из них строится история цен
                if p := r["purchase"]:
                    review.set_purchase(
                        Purchase(
                            price=p["price"],
                            weight=p["weight"],
                            harvest_year=p["harvestYear"],
                            harvest_season=Season.from_slug(p["harvestSeason"]) if p["harvestSeason"] else None,
                        )
                    )
            elif i % 2 == 0:
                o = offers[(r["tea"], r["shop"])]
                season = o["harvestSeason"]
                review.set_purchase(
                    Purchase(
                        price=o["price"],
                        weight=o["weight"],
                        harvest_year=o["harvestYear"],
                        harvest_season=Season.from_slug(season) if season else None,
                    )
                )
            review.set_infusion(infusion)
            self.db.add(review)
            created += 1
        return created

    async def load_diary(self) -> int:
        """Записи дневника демо-пользователей; повтор — по (пользователь, чай, дата)."""
        existing = set(await self.db.execute(select(DiaryEntry.user_id, DiaryEntry.tea_id, DiaryEntry.date)))
        created = 0
        for e in self.data.get("diary", []):
            day = date.fromisoformat(e["date"])
            key = (self.users[e["user"]], self.teas[e["tea"]], day)
            if key in existing:
                continue
            self.db.add(
                DiaryEntry(
                    user_id=key[0],
                    tea_id=key[1],
                    shop_id=self.shops[e["shop"]],
                    date=day,
                    rating=e["rating"],
                    water=e["water"],
                    grams=Decimal(str(e["grams"])),
                    volume=e["volume"],
                    infusions=e["infusions"],
                    text=e["text"],
                )
            )
            existing.add(key)
            created += 1
        return created


async def main() -> None:
    parser = argparse.ArgumentParser(description="Заполнить БД демо-данными")
    parser.add_argument("--author", metavar="EMAIL", help="автор добавленных чаёв и предложений")
    args = parser.parse_args()

    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    async with SessionFactory() as db:
        author_id = None
        if args.author:
            author_id = await db.scalar(select(User.id).where(User.email == args.author.lower()))
            if author_id is None:
                raise SystemExit(f"Пользователь {args.author} не найден")
        stats = await CatalogSeeder(db, data, author_id).run()
    await engine.dispose()
    print("Готово:", ", ".join(f"{k}: {v}" for k, v in stats.items()))


if __name__ == "__main__":
    asyncio.run(main())
