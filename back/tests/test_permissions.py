"""Права: чужое не удалить, за себя не проголосовать, без входа — 401."""

from back.tests.conftest import make_shop, make_tea


async def test_anonymous_gets_401(client):
    for method, url in [
        ("get", "/api/diary"),
        ("get", "/api/me/shelf"),
        ("get", "/api/me/recommendations"),
        ("get", "/api/me/feed"),
        ("put", "/api/me/shelf/1"),
        ("put", "/api/users/1/follow"),
        ("put", "/api/reviews/1/vote"),
    ]:
        kwargs = {"json": {}} if method == "put" else {}
        assert (await getattr(client, method)(url, **kwargs)).status_code == 401, url


async def _review(c, tea_id, shop_id, **extra) -> dict:
    r = await c.post(
        f"/api/teas/{tea_id}/reviews", json={"shopId": shop_id, "rating": 4, "text": "Хороший чай, советую."} | extra
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_cannot_delete_someone_elses_review(client, user, other):
    shop = await make_shop()
    tea = await make_tea("Дянь Хун", shops=[shop])
    other_client, _ = other
    review = await _review(other_client, tea, shop)
    assert (await client.delete(f"/api/reviews/{review['id']}")).status_code == 404
    assert (await other_client.delete(f"/api/reviews/{review['id']}")).status_code == 204


async def test_helpful_votes(client, user, other):
    shop = await make_shop()
    tea = await make_tea("Дянь Хун", shops=[shop])
    other_client, _ = other
    review = await _review(other_client, tea, shop)

    # За свой отзыв — нельзя
    assert (await other_client.put(f"/api/reviews/{review['id']}/vote", json={"helpful": True})).status_code == 403
    # Чужой — можно, повтор не удваивает, снятие обнуляет
    for _ in range(2):
        r = await client.put(f"/api/reviews/{review['id']}/vote", json={"helpful": True})
        assert r.json()["helpful"] == 1 and r.json()["voted"] is True
    tea_page = (await client.get(f"/api/teas/{tea}")).json()
    assert tea_page["reviews"][0]["voted"] is True
    r = await client.put(f"/api/reviews/{review['id']}/vote", json={"helpful": False})
    assert r.json()["helpful"] == 0


async def test_follow_rules(client, user, other):
    _, maria = other
    assert (await client.put(f"/api/users/{user['id']}/follow", json={"follow": True})).status_code == 403
    r = await client.put(f"/api/users/{maria['id']}/follow", json={"follow": True})
    assert r.json()["followers"] == 1 and r.json()["followedByMe"] is True
    assert [u["id"] for u in (await client.get("/api/me/following")).json()] == [maria["id"]]
    assert (await client.put("/api/users/999999/follow", json={"follow": True})).status_code == 404


async def test_feed_shows_followed_authors_only(client, user, other):
    shop = await make_shop()
    tea = await make_tea("Дянь Хун", shops=[shop])
    other_client, maria = other
    await _review(other_client, tea, shop)
    assert (await client.get("/api/me/feed")).json() == []
    await client.put(f"/api/users/{maria['id']}/follow", json={"follow": True})
    feed = (await client.get("/api/me/feed")).json()
    assert [r["user"]["name"] for r in feed] == ["Мария"]


async def test_diary_is_private(client, user, other):
    shop = await make_shop()
    tea = await make_tea("Дянь Хун", shops=[shop])
    entry = {"teaId": tea, "shopId": shop, "date": "2026-10-01", "rating": 5, "water": 90, "grams": 5, "infusions": 6}
    created = (await client.post("/api/diary", json=entry)).json()
    other_client, _ = other
    assert (await other_client.get("/api/diary")).json() == []
    assert (await other_client.delete(f"/api/diary/{created['id']}")).status_code == 404


async def test_catalog_cannot_be_deleted(client, user):
    """Чаи и магазины у чая не удаляет никто, даже автор: каталог только пополняется."""
    shop = await make_shop()
    tea = await make_tea("Шу Пуэр", shops=[shop])
    assert (await client.delete(f"/api/teas/{tea}")).status_code == 405
    assert (await client.delete(f"/api/teas/{tea}/offers/{shop}")).status_code == 405
    assert (await client.get(f"/api/teas/{tea}")).status_code == 200
