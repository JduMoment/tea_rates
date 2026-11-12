"""robots.txt, sitemap.xml и подтверждение Яндекс Вебмастера."""

from back.tests.conftest import add_review, add_user, make_shop, make_tea


async def test_robots_txt(client):
    r = await client.get("/robots.txt")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/plain")
    assert "Disallow: /api/" in r.text and "Disallow: /diary" in r.text
    assert "Sitemap: https://5listov.test/sitemap.xml" in r.text


async def test_sitemap_lists_teas_shops_and_authors(client):
    shop = await make_shop()
    tea = await make_tea("Дянь Хун", shops=[shop])
    author = await add_user("a@b.ru")
    silent = await add_user("c@d.ru")
    await add_review(author, tea, shop, 5)

    r = await client.get("/sitemap.xml")
    assert r.status_code == 200 and r.headers["content-type"] == "application/xml"
    xml = r.text
    for path in ("/", "/rankings/categories/gaba", f"/teas/{tea}", "/shops/daochain", f"/users/{author}"):
        assert f"<loc>https://5listov.test{path}</loc>" in xml, path
    assert f"/users/{silent}<" not in xml  # профиль без отзывов не нужен в поиске
    assert "<lastmod>" in xml


async def test_yandex_verification_file(client):
    r = await client.get("/yandex_c783dcee21598c7b.html")
    assert r.status_code == 200 and "Verification: c783dcee21598c7b" in r.text
