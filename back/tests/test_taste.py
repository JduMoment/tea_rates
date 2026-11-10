"""Поиск по вкусу, вкусовой профиль и «Вам может понравиться»."""

from back.enums.flavor import Flavor
from back.services.flavors import FlavorProfile
from back.services.recommendations import UserTaste
from back.tests.conftest import add_review, add_user, make_shop, make_tea

H, A, R, S, G = Flavor.HONEY, Flavor.DRIED_APRICOT, Flavor.RAISIN, Flavor.SPINACH, Flavor.CUT_GRASS


async def _catalog():
    shop = await make_shop()
    honeyed = await make_tea("Медовый", shops=[shop])
    fruity = await make_tea("Сухофруктовый", shops=[shop])
    grassy = await make_tea("Травяной", shops=[shop])
    silent = await make_tea("Неописанный", shops=[shop])
    a, b = await add_user("a@example.com"), await add_user("b@example.com")
    await add_review(a, honeyed, shop, 5, [H, A])
    await add_review(b, honeyed, shop, 5, [H])
    await add_review(a, fruity, shop, 4, [A, R])
    await add_review(a, grassy, shop, 3, [S, G])
    await add_review(b, silent, shop, 4, [])
    return shop, honeyed, fruity, grassy, silent


async def test_flavor_search_orders_by_matches_and_lists_undescribed_last(client):
    _, honeyed, fruity, grassy, silent = await _catalog()
    teas = (await client.get("/api/teas?flavor=honey&flavor=dried_apricot")).json()
    ids = [t["id"] for t in teas]
    assert ids == [honeyed, fruity, silent]  # травяной не подходит — его нет
    assert teas[0]["flavorMatch"] == {"flavors": ["honey", "dried_apricot"], "share": 1.0}
    assert teas[1]["flavorMatch"]["flavors"] == ["dried_apricot"]
    assert teas[2]["flavorMatch"] is None  # о вкусе не писали
    assert grassy not in ids


async def test_flavor_search_rejects_unknown_note(client):
    assert (await client.get("/api/teas?flavor=bergamot")).status_code == 422


async def test_user_taste_profile(client, user):
    shop = await make_shop()
    tea = await make_tea("Медовый", shops=[shop])
    await add_review(user["id"], tea, shop, 5, [H, A])
    profile = (await client.get(f"/api/users/{user['id']}/flavors")).json()
    assert profile["reviews"] == 1
    assert {s["slug"] for s in profile["flavors"]} == {"honey", "dried_apricot"}


def test_user_taste_weights_follow_ratings():
    taste = UserTaste([(5, [H]), (4, [A]), (3, [S]), (2, [G])])
    assert (taste.flavors[H], taste.flavors[A], taste.flavors[S], taste.flavors[G]) == (2, 1, 0, -1)
    assert taste.likes_something
    assert not UserTaste([(3, [H]), (2, [S])]).likes_something


def test_similar_profile_scores_higher():
    taste = UserTaste([(5, [H, A]), (5, [R, A])])
    sweet = FlavorProfile.of([[H, A], [A, R]])
    grassy = FlavorProfile.of([[S, G], [G]])
    score_sweet, reasons = taste.similarity(sweet)
    score_grassy, _ = taste.similarity(grassy)
    assert score_sweet > 0.5 > score_grassy == 0
    assert reasons[0] == A  # общая нота с самым большим весом


async def test_recommendations(client, user):
    shop, honeyed, fruity, grassy, silent = await _catalog()
    # Мало своих отзывов с нотами — советов нет, но видно, сколько осталось
    empty = (await client.get("/api/me/recommendations")).json()
    assert empty == {"reviews": 0, "needed": 3, "items": []}

    liked = await make_tea("Любимый", shops=[shop])
    for title in ("Свой 1", "Свой 2"):
        await add_review(user["id"], await make_tea(title, shops=[shop]), shop, 5, [H, A])
    await add_review(user["id"], liked, shop, 5, [H, R])
    recs = (await client.get("/api/me/recommendations")).json()
    ids = [i["tea"]["id"] for i in recs["items"]]
    assert recs["reviews"] == 3
    assert ids[0] == honeyed and fruity in ids
    assert grassy not in ids and silent not in ids  # не похож / не описан
    assert liked not in ids  # уже пробовал
    assert "honey" in recs["items"][0]["reasons"]
