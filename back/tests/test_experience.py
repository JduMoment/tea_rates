"""Опыт автора: строка под именем в отзыве и разбивка по видам на странице автора."""

from io import BytesIO

from PIL import Image

from back.enums.tea_kind import TeaKind
from back.tests.conftest import add_review, add_user, make_shop, make_tea


async def _author_with_history() -> tuple[int, int, int]:
    """Автор оценил 3 шу пуэра и улун в двух магазинах. Возвращает (автор, шу пуэр, магазин)."""
    a = await make_shop("a", "Магазин А")
    b = await make_shop("b", "Магазин Б")
    uid = await add_user("pro@example.com", "Знаток")
    shu = [await make_tea(f"Шу {i}", TeaKind.SHU, shops=[a, b]) for i in range(3)]
    oolong = await make_tea("Те Гуань Инь", TeaKind.OOLONG, shops=[a])
    for tea in shu:
        await add_review(uid, tea, a, 4)
    await add_review(uid, shu[0], b, 5)  # тот же чай из другого магазина — чаёв не прибавляет
    await add_review(uid, oolong, a, 5)
    return uid, shu[0], a


async def test_review_shows_author_experience(client):
    _, shu, _ = await _author_with_history()
    newbie = await add_user("new@example.com", "Новичок")
    shop = await make_shop("c", "Магазин В")
    gaba = await make_tea("Габа", TeaKind.GABA, shops=[shop])
    await add_review(newbie, gaba, shop, 5)

    tea = (await client.get(f"/api/teas/{shu}")).json()
    exp = {r["user"]["name"]: r["user"]["experience"] for r in tea["reviews"]}["Знаток"]
    assert exp == {"teas": 4, "kinds": 2, "shops": 2, "sameKind": 3, "kindGenitive": "шу пуэров"}

    recent = (await client.get("/api/reviews", params={"limit": 50})).json()
    by_name = {r["user"]["name"]: r["user"]["experience"] for r in recent}
    assert by_name["Новичок"] == {"teas": 1, "kinds": 1, "shops": 1, "sameKind": 1, "kindGenitive": "габ"}


async def test_author_page_breaks_down_by_kind(client):
    uid, _, _ = await _author_with_history()
    a = (await client.get(f"/api/users/{uid}")).json()
    assert a["teas"] == 4
    assert a["shops"] == 2
    assert [(k["name"], k["teas"]) for k in a["kinds"]] == [("Шу пуэр", 3), ("Улун", 1)]  # больше — первым


async def test_author_preview_image(client):
    uid, _, _ = await _author_with_history()
    r = await client.get(f"/og/users/{uid}.png")
    assert r.status_code == 200
    assert Image.open(BytesIO(r.content)).size == (1200, 630)
