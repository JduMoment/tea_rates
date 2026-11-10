"""Картинки каталога: фото чая и логотип магазина — любой, пока картинки нет; заменить нельзя; обработка."""

from io import BytesIO

from PIL import Image

from back.core.db import SessionFactory
from back.models import Shop, Tea
from back.tests.conftest import MEDIA, make_shop, make_tea


def png(size=(2000, 1500), mode="RGB") -> bytes:
    out = BytesIO()
    Image.new(mode, size, (200, 60, 40, 0) if mode == "RGBA" else (200, 60, 40)).save(out, "PNG")
    return out.getvalue()


def files(data: bytes) -> dict:
    return {"file": ("pic.png", data, "image/png")}


def media(url: str):
    return MEDIA / url.removeprefix("/media/")


async def set_author(model, obj_id: int, user_id: int) -> None:
    async with SessionFactory() as db:
        (await db.get(model, obj_id)).author_id = user_id
        await db.commit()


async def test_tea_image_rules(client, user, other):
    shop = await make_shop()
    tea = await make_tea("Дянь Хун", shops=[shop])
    await set_author(Tea, tea, user["id"])
    other_client, _ = other

    # Картинки нет — поставить может и не автор
    r = await other_client.put(f"/api/teas/{tea}/image", files=files(png()))
    assert r.status_code == 200, r.text
    first = r.json()
    with Image.open(media(first["url"])) as big, Image.open(media(first["thumbUrl"])) as thumb:
        assert big.format == "WEBP" and max(big.size) == 1200 and max(thumb.size) == 480

    # Картинка есть — заменить не может никто, даже автор
    assert (await client.put(f"/api/teas/{tea}/image", files=files(png()))).status_code == 403
    assert media(first["url"]).exists()

    page = (await client.get(f"/api/teas/{tea}")).json()
    assert page["imageUrl"] == first["url"] and page["thumbUrl"] == first["thumbUrl"]
    listed = (await client.get("/api/teas")).json()
    assert listed[0]["thumbUrl"] == first["thumbUrl"]


async def test_shop_logo_keeps_transparency(client, user, other):
    shop = await make_shop()
    await set_author(Shop, shop, user["id"])
    other_client, _ = other
    r = await other_client.put(f"/api/shops/{shop}/logo", files=files(png((800, 400), "RGBA")))
    assert r.status_code == 200, r.text
    with Image.open(media(r.json()["url"])) as logo:
        assert logo.size == (256, 128) and logo.mode == "RGBA"
    assert (await client.put(f"/api/shops/{shop}/logo", files=files(png()))).status_code == 403

    tea = await make_tea("Дянь Хун", shops=[shop])
    page = (await client.get(f"/api/teas/{tea}")).json()
    assert page["offers"][0]["shop"]["logoUrl"].startswith("/media/shops/")
    assert (await client.get("/api/shops/daochain")).json()["authorId"] == user["id"]


async def test_catalog_image_validation(client, user):
    shop = await make_shop()
    tea = await make_tea("Дянь Хун", shops=[shop])
    await set_author(Tea, tea, user["id"])
    await set_author(Shop, shop, user["id"])
    bad = {"file": ("x.png", b"not an image", "image/png")}
    assert (await client.put(f"/api/teas/{tea}/image", files=bad)).status_code == 422
    assert (await client.put(f"/api/shops/{shop}/logo", files=bad)).status_code == 422
    assert (await client.put("/api/teas/9999/image", files=files(png()))).status_code == 404
    anon = client.__class__(transport=client._transport, base_url=client.base_url)
    assert (await anon.put(f"/api/teas/{tea}/image", files=files(png()))).status_code == 401
