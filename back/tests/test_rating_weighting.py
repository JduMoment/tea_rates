"""Оценки магазинов и чаёв учитывают опыт и щедрость авторов: пятёрки новичков не выводят низкосортный
чай и магазин с ним выше тех, которые хвалят перепробовавшие много чая."""

from back.enums.tea_kind import TeaKind
from back.tests.conftest import add_review, add_user, make_shop, make_tea


async def _shops(client) -> dict[str, dict]:
    r = await client.get("/api/shops")
    assert r.status_code == 200, r.text
    return {s["name"]: s for s in r.json()}


async def _experienced(email: str, shop: int, ratings: list[int]) -> int:
    """Автор, оценивший len(ratings) разных чаёв в магазине shop."""
    uid = await add_user(email)
    for i, rating in enumerate(ratings):
        tea = await make_tea(f"Чай {email} {i}", TeaKind.SHU, shops=[shop])
        await add_review(uid, tea, shop, rating)
    return uid


async def test_newcomers_fives_do_not_beat_experienced_praise(client):
    good = await make_shop("daochai", "ДаоЧай")
    market = await make_shop("market", "Продавец с маркетплейса")
    # Трое опытных: каждый оценил по 10 чаёв ДаоЧая, в среднем 4.4
    for n in range(3):
        await _experienced(f"pro{n}@example.com", good, [5, 4, 4, 5, 4, 5, 4, 4, 5, 4])
    # Пятеро новичков: по одному чаю с маркетплейса, все на 5
    cheap = await make_tea("Шу в брикете", TeaKind.SHU, shops=[market])
    for n in range(5):
        await add_review(await add_user(f"new{n}@example.com"), cheap, market, 5)

    shops = await _shops(client)
    assert list(shops) == ["daochai", "market"]  # список магазинов — лучшие первыми
    assert shops["daochai"]["stats"]["avg"] > shops["market"]["stats"]["avg"]  # цифры совпадают с порядком
    assert shops["market"]["stats"]["reviews"] == 5  # число отзывов показываем честное

    r = await client.get("/api/rankings/shops")
    assert r.status_code == 200, r.text
    assert [row["shop"]["name"] for row in r.json()][:2] == ["daochai", "market"]


async def test_generous_author_counts_less_than_strict(client):
    """Одинаково опытные авторы ставят по пятёрке разным магазинам. Пятёрка того, кто обычно ставит 3,
    значит больше, чем пятёрка того, кто ставит 5 всему."""
    a = await make_shop("a", "Магазин А")
    b = await make_shop("b", "Магазин Б")
    elsewhere = await make_shop("other", "Где-то ещё")
    generous = await _experienced("generous@example.com", elsewhere, [5] * 9)
    strict = await _experienced("strict@example.com", elsewhere, [3] * 9)
    tea_a = await make_tea("Чай А", TeaKind.SHU, shops=[a])
    tea_b = await make_tea("Чай Б", TeaKind.SHU, shops=[b])
    await add_review(generous, tea_a, a, 5)
    await add_review(strict, tea_b, b, 5)

    shops = await _shops(client)
    assert shops["b"]["stats"]["avg"] > shops["a"]["stats"]["avg"]
    assert 1 <= shops["a"]["stats"]["avg"] <= 5


async def test_single_review_barely_adjusted(client):
    """Один отзыв — ещё не привычка: оценка остаётся близкой к поставленной."""
    shop = await make_shop()
    await make_shop("other", "Другой")
    tea = await make_tea("Габа", TeaKind.GABA, shops=[shop])
    other_tea = await make_tea("Улун", TeaKind.OOLONG, shops=[shop])
    await add_review(await add_user("x@example.com"), tea, shop, 5)
    await add_review(await add_user("y@example.com"), other_tea, shop, 3)

    stats = (await _shops(client))["daochain"]["stats"]
    assert stats["reviews"] == 2
    # Поправки симметричны и гасят друг друга: средняя 4.0 при весе 2 × 0.2, затем сглаживание к 3.5
    assert abs(stats["avg"] - (4.0 * 0.4 + 3.5 * 2) / (0.4 + 2)) < 0.01


async def test_tea_scores_weighted_too(client):
    """Чаи считаются так же: брикет с пятёрками новичков не обходит габу, которую хвалят опытные."""
    shop = await make_shop()
    elsewhere = await make_shop("other", "Где-то ещё")
    gaba = await make_tea("Габа Алишань", TeaKind.GABA, shops=[shop])
    brick = await make_tea("Шу в брикете", TeaKind.SHU, shops=[shop])
    for n in range(3):
        pro = await _experienced(f"pro{n}@example.com", elsewhere, [4, 5, 4, 4, 5, 4, 4, 5, 4])
        await add_review(pro, gaba, shop, 4 + n % 2)
    for n in range(5):
        await add_review(await add_user(f"new{n}@example.com"), brick, shop, 5)

    r = await client.get("/api/teas")
    assert r.status_code == 200, r.text
    titles = [t["title"] for t in r.json() if t["title"] in ("Габа Алишань", "Шу в брикете")]
    assert titles == ["Габа Алишань", "Шу в брикете"]
    avg = {t["title"]: t["stats"]["avg"] for t in r.json()}
    assert avg["Габа Алишань"] > avg["Шу в брикете"]  # цифры совпадают с порядком
    tea = (await client.get(f"/api/teas/{brick}")).json()
    assert tea["stats"]["reviews"] == 5
