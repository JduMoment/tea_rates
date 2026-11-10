"""«Как заваривают», история цен и сортировка по цене, шкаф «Мои чаи»."""

from decimal import Decimal

from back.enums.tea_kind import TeaKind
from back.tests.conftest import add_diary, add_review, add_user, make_shop, make_tea


async def test_brewing_falls_back_to_typical_until_enough_entries(client):
    shop = await make_shop()
    tea = await make_tea("Лунцзин", TeaKind.GREEN, shops=[shop])
    a = await add_user("a@example.com")
    for _ in range(3):  # три записи, но один человек — мало
        await add_diary(a, tea, shop)
    b = (await client.get(f"/api/teas/{tea}/brewing")).json()
    assert b["community"] is None
    assert b["typical"] == {"water": [75, 80], "gramsPer100": [3.0, 4.0], "infusions": [3, 4]}
    assert b["category"] == "Зелёные"


async def test_brewing_medians_per_100ml(client):
    shop = await make_shop()
    tea = await make_tea("Да Хун Пао", TeaKind.OOLONG, shops=[shop])
    a, b = await add_user("a@example.com"), await add_user("b@example.com")
    await add_diary(a, tea, shop, water=95, grams=Decimal(6), volume=100, infusions=8, rating=5)
    await add_diary(b, tea, shop, water=90, grams=Decimal(9), volume=150, infusions=7, rating=5)
    await add_diary(b, tea, shop, water=99, grams=Decimal(4), volume=None, infusions=5, rating=2)
    brew = (await client.get(f"/api/teas/{tea}/brewing")).json()
    c = brew["community"]
    assert (c["entries"], c["people"], c["water"], c["infusions"]) == (3, 2, 95, 7)
    assert c["volume"] == 125 and c["gramsPer100"] == 6.0  # только записи с объёмом: 6 г/100 мл в обеих
    assert brew["liked"] is None  # понравилось только в двух записях — мало для сводки


async def test_price_history_and_sort(client):
    cheap_shop, dear_shop = await make_shop("a", "A"), await make_shop("b", "B")
    cheap = await make_tea("Дешёвый", shops=[cheap_shop], price=500, weight=100)  # 5 ₽/г
    dear = await make_tea("Дорогой", shops=[dear_shop], price=2000, weight=50)  # 40 ₽/г
    unpriced = await make_tea("Без цены", shops=[cheap_shop])
    u = await add_user("u@example.com")
    await add_review(u, dear, dear_shop, 5, price=2200)

    ids = [t["id"] for t in (await client.get("/api/teas?sort=price")).json()]
    assert ids == [cheap, dear, unpriced]

    history = (await client.get(f"/api/teas/{dear}/prices")).json()
    assert len(history) == 1 and history[0]["shop"]["name"] == "b"
    points = history[0]["points"]
    assert [(p["source"], p["perGram"]) for p in points] == [("offer", 40.0), ("review", 44.0)]


async def test_shelf_statuses_and_diary_moves_tea_home(client, user):
    shop = await make_shop()
    tea = await make_tea("Дянь Хун", shops=[shop])
    assert (await client.put(f"/api/me/shelf/{tea}", json={"status": "want"})).json()["status"] == "want"
    assert (await client.put(f"/api/me/shelf/{tea}", json={"status": "later"})).status_code == 422

    entry = {
        "teaId": tea,
        "shopId": shop,
        "date": "2026-10-01",
        "rating": 5,
        "water": 90,
        "grams": 5,
        "volume": 120,
        "infusions": 6,
    }
    saved = (await client.post("/api/diary", json=entry)).json()
    assert saved["volume"] == 120
    shelf = (await client.get("/api/me/shelf")).json()
    assert [(i["tea"]["id"], i["status"]) for i in shelf] == [(tea, "have")]  # заварил → «есть дома»

    # «Хочу повторить», а потом снова заварил — значит, купил ещё раз: опять «есть дома»
    assert (await client.put(f"/api/me/shelf/{tea}", json={"status": "repeat"})).json()[
        "statusLabel"
    ] == "Хочу повторить"
    await client.post("/api/diary", json=entry | {"date": "2026-10-05"})
    assert (await client.get("/api/me/shelf")).json()[0]["status"] == "have"

    assert (await client.delete(f"/api/me/shelf/{tea}")).status_code == 204
    assert (await client.get("/api/me/shelf")).json() == []


async def test_diary_volume_validation(client, user):
    shop = await make_shop()
    tea = await make_tea("Дянь Хун", shops=[shop])
    entry = {"teaId": tea, "shopId": shop, "date": "2026-10-01", "rating": 5, "water": 90, "grams": 5, "infusions": 6}
    assert (await client.post("/api/diary", json=entry | {"volume": 5})).status_code == 422
    assert (await client.post("/api/diary", json=entry | {"date": "2099-01-01"})).status_code == 422
