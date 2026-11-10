"""Отзывы: шкалы настоя, замена отзыва, фото (EXIF, лимиты, удаление файлов)."""

from io import BytesIO

from PIL import Image

from back.tests.conftest import MEDIA, make_shop, make_tea

TEXT = "Хороший чай, советую."


async def test_review_with_infusion_and_replace(client, user):
    shop = await make_shop()
    tea = await make_tea("Дянь Хун", shops=[shop])
    body = {"shopId": shop, "rating": 4, "text": TEXT, "flavors": ["honey"], "body": 4, "strength": 3}
    first = (await client.post(f"/api/teas/{tea}/reviews", json=body)).json()
    assert (first["body"], first["strength"], first["aftertaste"]) == (4, 3, None)

    # Повторный отзыв на тот же чай из того же магазина заменяет прежний
    second = (await client.post(f"/api/teas/{tea}/reviews", json=body | {"rating": 5, "aftertaste": 5})).json()
    assert second["id"] == first["id"] and second["rating"] == 5
    page = (await client.get(f"/api/teas/{tea}")).json()
    assert len(page["reviews"]) == 1
    assert page["infusion"] == {"body": 4.0, "strength": 3.0, "aftertaste": 5.0, "astringency": None, "reviews": 1}


async def test_review_validation(client, user):
    shop = await make_shop()
    tea = await make_tea("Дянь Хун", shops=[shop])
    other_shop = await make_shop("tea-harbor", "Tea Harbor")
    bad = [
        {"shopId": shop, "rating": 4, "text": TEXT, "body": 9},  # шкала 1–5
        {"shopId": shop, "rating": 4, "text": TEXT, "flavors": ["nope"]},  # нет такой ноты
        {"shopId": shop, "rating": 4, "text": "коротко"},  # слишком короткий текст
        {"shopId": shop, "rating": 4, "text": TEXT, "price": 100},  # цена без веса
    ]
    for body in bad:
        assert (await client.post(f"/api/teas/{tea}/reviews", json=body)).status_code == 422, body
    # Отзыв только на покупку в магазине, где чай продаётся
    r = await client.post(f"/api/teas/{tea}/reviews", json={"shopId": other_shop, "rating": 4, "text": TEXT})
    assert r.status_code == 404


def jpeg_with_exif() -> bytes:
    """3000×2000, в EXIF — геопозиция, модель телефона и поворот на 90°."""
    img = Image.new("RGB", (3000, 2000), (180, 120, 60))
    exif = Image.Exif()
    exif[0x0110] = "SecretPhone 15"
    exif[0x0112] = 6
    exif[0x8825] = {1: "N", 2: (55.0, 45.0, 0.0), 3: "E", 4: (37.0, 37.0, 0.0)}
    out = BytesIO()
    img.save(out, "JPEG", exif=exif.tobytes())
    return out.getvalue()


async def _my_review(client) -> int:
    shop = await make_shop()
    tea = await make_tea("Дянь Хун", shops=[shop])
    return (await client.post(f"/api/teas/{tea}/reviews", json={"shopId": shop, "rating": 5, "text": TEXT})).json()[
        "id"
    ]


async def test_photo_is_resized_rotated_and_stripped(client, user):
    review_id = await _my_review(client)
    r = await client.post(f"/api/reviews/{review_id}/photos", files={"file": ("p.jpg", jpeg_with_exif(), "image/jpeg")})
    assert r.status_code == 201, r.text
    photo = r.json()["photos"][0]
    assert (photo["width"], photo["height"]) == (1067, 1600)  # повернули по EXIF и уменьшили

    served = await client.get(photo["url"])
    assert served.status_code == 200 and served.headers["content-type"] == "image/webp"
    stored = Image.open(BytesIO(served.content))
    assert stored.format == "WEBP"
    assert not stored.getexif() and "exif" not in stored.info  # метаданные удалены
    assert (await client.get(photo["thumbUrl"])).status_code == 200


async def test_photo_limits(client, user, other):
    review_id = await _my_review(client)
    url = f"/api/reviews/{review_id}/photos"
    r = await client.post(url, files={"file": ("x.jpg", b"not an image", "image/jpeg")})
    assert r.status_code == 422
    small = BytesIO()
    Image.new("RGB", (50, 50)).save(small, "PNG")
    for _ in range(3):
        assert (await client.post(url, files={"file": ("a.png", small.getvalue(), "image/png")})).status_code == 201
    assert (await client.post(url, files={"file": ("a.png", small.getvalue(), "image/png")})).status_code == 409
    # Чужой отзыв — как будто его нет
    other_client, _ = other
    assert (await other_client.post(url, files={"file": ("a.png", small.getvalue(), "image/png")})).status_code == 404


async def test_deleting_review_removes_files(client, user):
    review_id = await _my_review(client)
    small = BytesIO()
    Image.new("RGB", (50, 50)).save(small, "PNG")
    await client.post(f"/api/reviews/{review_id}/photos", files={"file": ("a.png", small.getvalue(), "image/png")})
    assert len(list((MEDIA / "reviews" / str(review_id)).iterdir())) == 2  # фото и превью
    assert (await client.delete(f"/api/reviews/{review_id}")).status_code == 204
    assert list((MEDIA / "reviews" / str(review_id)).iterdir()) == []


async def test_media_path_traversal_is_blocked(client):
    assert (await client.get("/media/../../etc/passwd")).status_code == 404


async def test_edit_review_keeps_date(client, user, other):
    shop = await make_shop()
    tea = await make_tea("Дянь Хун", shops=[shop])
    body = {"shopId": shop, "rating": 4, "text": TEXT, "price": 1000, "weight": 50}
    first = (await client.post(f"/api/teas/{tea}/reviews", json=body)).json()
    assert first["editedAt"] is None

    # Правка: дата прежняя, появляется «изменён»; магазин в правке не передаётся
    edit = {"rating": 5, "text": "Перепробовал — лучше, чем думал.", "price": 1000, "weight": 50, "flavors": ["honey"]}
    r = await client.put(f"/api/reviews/{first['id']}", json=edit)
    assert r.status_code == 200, r.text
    edited = r.json()
    assert edited["id"] == first["id"] and edited["createdAt"] == first["createdAt"]
    assert edited["editedAt"] and (edited["rating"], edited["flavors"]) == (5, ["honey"])

    # Чужой отзыв не поправить — для чужого его «нет»
    other_client, _ = other
    assert (await other_client.put(f"/api/reviews/{first['id']}", json=edit)).status_code == 404
    assert (await client.put(f"/api/reviews/{first['id']}", json=edit | {"rating": 9})).status_code == 422

    # Новый отзыв на тот же магазин — новая покупка: свежая дата, пометка снимается
    again = (await client.post(f"/api/teas/{tea}/reviews", json=body)).json()
    assert again["id"] == first["id"] and again["editedAt"] is None and again["createdAt"] > first["createdAt"]


async def test_marked_tastes_and_astringency(client, user, other):
    """Вкус отмечают сами; у отзыва без отмеченного вкуса он выводится из нот (как у старых)."""
    shop = await make_shop()
    tea = await make_tea("Лунцзин", shops=[shop])
    other_client, _ = other
    # Ноты все «сладкие», но автор сам отметил сладкий и умами
    mine = {"shopId": shop, "rating": 5, "text": TEXT, "flavors": ["pumpkin", "seeds"], "tastes": ["sweet", "umami"]}
    r = (await client.post(f"/api/teas/{tea}/reviews", json=mine | {"astringency": 2})).json()
    assert r["tastes"] == ["sweet", "umami"] and r["astringency"] == 2
    # Второй автор вкус не отметил — выводится из нот: цитрус → кислый
    await other_client.post(
        f"/api/teas/{tea}/reviews", json={"shopId": shop, "rating": 4, "text": TEXT, "flavors": ["citrus"]}
    )

    page = (await client.get(f"/api/teas/{tea}")).json()
    tastes = {t["slug"]: t["share"] for t in page["flavorProfile"]["tastes"]}
    assert tastes == {"sweet": 0.5, "umami": 0.5, "sour": 0.5}
    assert page["infusion"]["astringency"] == 2.0

    # Вкус без нот тоже считается
    await client.put(f"/api/reviews/{r['id']}", json={"rating": 5, "text": TEXT, "tastes": ["umami"]})
    page = (await client.get(f"/api/teas/{tea}")).json()
    assert {t["slug"]: t["share"] for t in page["flavorProfile"]["tastes"]} == {"umami": 0.5, "sour": 0.5}

    bad = mine | {"tastes": ["spicy"]}
    assert (await client.post(f"/api/teas/{tea}/reviews", json=bad)).status_code == 422
    assert (await client.post(f"/api/teas/{tea}/reviews", json=mine | {"flavors": ["wine"]})).status_code == 422
