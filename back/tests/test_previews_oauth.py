"""Превью ссылок (мета-теги и картинки) и вход через Яндекс."""

from io import BytesIO

from PIL import Image

from back.core.db import SessionFactory
from back.services.auth import AuthService
from back.services.oauth import OAuthProfile, YandexOAuth
from back.tests.conftest import add_user, make_shop, make_tea


async def test_tea_page_has_open_graph_tags(client, tmp_path, monkeypatch):
    # Фронт в тестах не собран — подложим минимальный index.html
    (tmp_path / "index.html").write_text("<html><head><title>x</title></head><body></body></html>", encoding="utf-8")
    monkeypatch.setattr("back.views.frontend.FRONT_DIST", tmp_path)
    shop = await make_shop()
    tea = await make_tea("Габа <Алишань>", shops=[shop])

    page = (await client.get(f"/teas/{tea}")).text
    assert "<title>Габа &lt;Алишань&gt; — 5 листов</title>" in page  # экранировано
    assert f'<meta property="og:image" content="https://5listov.test/og/teas/{tea}.png" />' in page
    assert f'<link rel="canonical" href="https://5listov.test/teas/{tea}" />' in page

    missing = await client.get("/teas/999999")
    assert "5 листов — рейтинг чаёв по магазинам" in missing.text  # несуществующий чай — общее превью
    assert (await client.get("/no-such-page")).status_code == 404


async def test_og_images(client):
    shop = await make_shop()
    tea = await make_tea("Дянь Хун", shops=[shop])
    for url in (f"/og/teas/{tea}.png", "/og/shops/daochain.png", "/og/default.png"):
        r = await client.get(url)
        assert r.status_code == 200 and r.headers["content-type"] == "image/png", url
        assert Image.open(BytesIO(r.content)).size == (1200, 630)
    assert (await client.get("/og/teas/999999.png")).status_code == 404


async def test_oauth_start_sets_state_and_callback_rejects_forgery(client, monkeypatch):
    monkeypatch.setattr(YandexOAuth, "configured", property(lambda self: True))
    r = await client.get("/api/auth/oauth/yandex/start?next=//evil.com", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("https://oauth.yandex.ru/authorize?")
    assert "code_challenge_method=S256" in r.headers["location"]
    assert "tea_oauth" in r.headers["set-cookie"]

    # state не совпадает с cookie — отказ
    r = await client.get("/api/auth/oauth/yandex/callback?code=x&state=forged", follow_redirects=False)
    assert r.headers["location"] == "/login?oauth_error=state"
    assert (await client.get("/api/auth/oauth/vk/start", follow_redirects=False)).status_code == 404


async def test_oauth_login_links_by_email_and_then_by_subject():
    existing = await add_user("ivan@yandex.ru", "Иван")
    async with SessionFactory() as db:
        auth = AuthService(db)
        linked = await auth.login_external("yandex", OAuthProfile("y-1", "ivan@yandex.ru", "Ваня"))
        assert linked.id == existing and linked.name == "Иван"  # привязали к существующему, имя не тронули
        again = await auth.login_external("yandex", OAuthProfile("y-1", "changed@yandex.ru", "Ваня"))
        assert again.id == existing  # почту в Яндексе сменили — узнаём по id
        fresh = await auth.login_external("yandex", OAuthProfile("y-2", "new@yandex.ru", "Новый"))
        assert fresh.id != existing and fresh.password_hash == "!"
        await db.commit()
