"""Пользователи добавляют магазины: сайт обязателен и уникален, похожие названия подсвечиваются."""

import pytest

from back.core.shop_url import BadShopUrl, shop_key
from back.tests.conftest import make_shop

SHOP = {"title": "Чайная лавка", "site": "https://chaynaya-lavka.ru", "city": "Москва"}


@pytest.mark.parametrize(
    ("url", "key"),
    [
        ("https://shop.ru", "shop.ru"),
        ("http://www.Shop.RU/catalog/puer?utm=1#top", "shop.ru"),
        ("shop.ru/", "shop.ru"),
        ("https://shop.ru:443", "shop.ru"),
        ("https://moscow.shop.ru", "moscow.shop.ru"),  # поддомен — может быть отдельным магазином
        ("https://чай.рф", "xn--80as4b.xn--p1ai"),
        ("xn--80as4b.xn--p1ai", "xn--80as4b.xn--p1ai"),
        ("https://vk.com/TeaShop?w=wall", "vk.com/teashop"),
        ("https://m.vk.com/teashop", "vk.com/teashop"),
        ("https://www.ozon.ru/seller/chay-123/products", "ozon.ru/seller/chay-123"),
        ("https://t.me/teashop", "t.me/teashop"),
    ],
)
def test_shop_key(url, key):
    assert shop_key(url) == key


@pytest.mark.parametrize("url", ["", "shop", "ftp://shop.ru", "https://vk.com", "https://t.me/", "javascript:alert(1)"])
def test_shop_key_rejects(url):
    with pytest.raises(BadShopUrl):
        shop_key(url)


async def test_create_shop(client, user):
    r = await client.post("/api/shops", json=SHOP)
    assert r.status_code == 201, r.text
    shop = r.json()
    assert shop["name"] == "chaynaya-lavka" and shop["title"] == "Чайная лавка" and shop["country"] == "Россия"
    assert (await client.get(f"/api/shops/{shop['name']}")).status_code == 200


async def test_same_site_is_rejected_in_any_spelling(client, user):
    await client.post("/api/shops", json=SHOP)
    for site in ("chaynaya-lavka.ru", "http://www.Chaynaya-Lavka.ru/catalog?x=1", "https://chaynaya-lavka.ru/"):
        r = await client.post("/api/shops", json=SHOP | {"title": "Другое имя", "site": site})
        assert r.status_code == 409, site
        assert "Чайная лавка" in r.json()["detail"]


async def test_same_name_gets_unique_slug(client, user):
    await client.post("/api/shops", json=SHOP)
    r = await client.post("/api/shops", json=SHOP | {"site": "https://lavka-spb.ru", "city": "Санкт-Петербург"})
    assert r.status_code == 201 and r.json()["name"] == "chaynaya-lavka-2"


async def test_shop_validation_and_auth(client):
    assert (await client.post("/api/shops", json=SHOP)).status_code == 401
    from back.tests.conftest import register

    await register(client)
    for bad in ({"site": ""}, {"site": "https://vk.com"}, {"title": "Ч"}, {"city": ""}):
        assert (await client.post("/api/shops", json=SHOP | bad)).status_code == 422, bad


async def test_check_finds_same_site_and_similar_titles(client):
    await make_shop("daochain", "DaoChain", site="https://example.com")
    same = (await client.get("/api/shops/check", params={"title": "Новый", "site": "www.example.com/tea"})).json()
    assert same["sameSite"]["name"] == "daochain" and same["siteKey"] == "example.com"

    for title in ("Dao Chain", "Даочайн", "daochain shop"):
        similar = (await client.get("/api/shops/check", params={"title": title})).json()
        assert [s["name"] for s in similar["similar"]] == ["daochain"], title

    unrelated = (await client.get("/api/shops/check", params={"title": "Горный лист"})).json()
    assert unrelated["similar"] == [] and unrelated["sameSite"] is None

    bad = (await client.get("/api/shops/check", params={"site": "vk.com"})).json()
    assert bad["siteError"] and bad["siteKey"] is None


async def test_shop_check_does_not_shadow_shop_pages(client):
    await make_shop("check-shop", "Check")
    assert (await client.get("/api/shops/check")).status_code == 200
    assert (await client.get("/api/shops/check-shop")).status_code == 200
