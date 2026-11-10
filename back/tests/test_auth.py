"""Регистрация, вход, выход и восстановление пароля."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from back.core.db import SessionFactory
from back.models import PasswordReset
from back.tests.conftest import new_client, register
from back.views import auth as auth_views


async def test_register_login_logout(client):
    await register(client, email="Ivan@Example.com")
    assert (await client.get("/api/auth/me")).json()["email"] == "ivan@example.com"
    assert (await client.post("/api/auth/logout")).status_code == 204
    assert (await client.get("/api/auth/me")).status_code == 401
    r = await client.post("/api/auth/login", json={"email": "IVAN@example.com", "password": "secret1"})
    assert r.status_code == 200


async def test_wrong_password_and_duplicate_email(client, user):
    r = await client.post("/api/auth/login", json={"email": user["email"], "password": "nope123"})
    assert r.status_code == 401
    r = await client.post("/api/auth/register", json={"name": "Двойник", "email": user["email"], "password": "secret1"})
    assert r.status_code == 409


@pytest.fixture
def mailbox(monkeypatch) -> list[dict]:
    """Письма вместо отправки складываются сюда."""
    sent: list[dict] = []

    async def fake_send(to: str, subject: str, text: str) -> None:
        sent.append({"to": to, "subject": subject, "text": text})

    monkeypatch.setattr(auth_views, "send_mail", fake_send)
    return sent


def token_from(letter: dict) -> str:
    return letter["text"].split("token=")[1].split()[0]


async def test_password_reset_flow(client, user, mailbox):
    async with new_client() as anon:
        assert (await anon.post("/api/auth/password/forgot", json={"email": user["email"]})).status_code == 204
        assert len(mailbox) == 1
        assert mailbox[0]["to"] == user["email"]
        assert "https://5listov.test/reset-password?token=" in mailbox[0]["text"]

        r = await anon.post("/api/auth/password/reset", json={"token": token_from(mailbox[0]), "password": "newpass1"})
        assert r.status_code == 200
        assert (await anon.get("/api/auth/me")).status_code == 200  # сразу вошёл

    # Старая сессия (client) завершена, старый пароль больше не подходит
    assert (await client.get("/api/auth/me")).status_code == 401
    bad = await client.post("/api/auth/login", json={"email": user["email"], "password": "secret1"})
    assert bad.status_code == 401
    good = await client.post("/api/auth/login", json={"email": user["email"], "password": "newpass1"})
    assert good.status_code == 200


async def test_reset_link_works_once(client, user, mailbox):
    await client.post("/api/auth/password/forgot", json={"email": user["email"]})
    token = token_from(mailbox[0])
    assert (
        await client.post("/api/auth/password/reset", json={"token": token, "password": "first12"})
    ).status_code == 200
    r = await client.post("/api/auth/password/reset", json={"token": token, "password": "second1"})
    assert r.status_code == 400


async def test_reset_link_expires(client, user, mailbox):
    await client.post("/api/auth/password/forgot", json={"email": user["email"]})
    async with SessionFactory() as db:
        await db.execute(update(PasswordReset).values(expires_at=datetime.now(UTC) - timedelta(minutes=1)))
        await db.commit()
    r = await client.post("/api/auth/password/reset", json={"token": token_from(mailbox[0]), "password": "newpass1"})
    assert r.status_code == 400


async def test_forgot_does_not_reveal_emails_and_is_rate_limited(client, user, mailbox):
    assert (await client.post("/api/auth/password/forgot", json={"email": "ghost@example.com"})).status_code == 204
    assert mailbox == []
    for _ in range(3):
        assert (await client.post("/api/auth/password/forgot", json={"email": user["email"]})).status_code == 204
    assert len(mailbox) == 1  # повтор в течение 2 минут — без письма


async def test_reset_rejects_short_password(client):
    r = await client.post("/api/auth/password/reset", json={"token": "x" * 40, "password": "123"})
    assert r.status_code == 422
