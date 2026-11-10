from sqlalchemy import select

from back.core.db import SessionFactory
from back.models import Feedback
from back.services.feedback import FEEDBACK_LIMIT
from back.views import feedback as feedback_views


async def _all() -> list[Feedback]:
    async with SessionFactory() as db:
        return list((await db.scalars(select(Feedback).order_by(Feedback.id))).all())


async def test_guest_can_send_feedback_and_it_is_mailed(client, monkeypatch):
    sent: list[dict] = []

    async def fake_send(to, subject, text, reply_to=None):
        sent.append({"to": to, "subject": subject, "text": text, "reply_to": reply_to})

    monkeypatch.setattr(feedback_views, "send_mail", fake_send)
    monkeypatch.setattr(feedback_views, "ALERT_EMAIL", "admin@example.com")
    r = await client.post(
        "/api/feedback",
        json={"text": "  Не грузится фото  ", "email": "Guest@Example.com", "page": "/teas/1"},
        headers={"User-Agent": "TestBrowser/1.0"},
    )
    assert r.status_code == 204, r.text
    [item] = await _all()
    assert (item.text, item.email, item.page, item.user_agent, item.user_id) == (
        "Не грузится фото",
        "guest@example.com",
        "/teas/1",
        "TestBrowser/1.0",
        None,
    )
    [letter] = sent
    assert letter["to"] == "admin@example.com" and letter["reply_to"] == "guest@example.com"
    assert "Не грузится фото" in letter["text"] and "https://5listov.test/teas/1" in letter["text"]


async def test_logged_in_user_email_is_taken_from_profile(client, user):
    assert (await client.post("/api/feedback", json={"text": "Идея"})).status_code == 204
    [item] = await _all()
    assert item.user_id == user["id"] and item.email == user["email"]


async def test_mail_failure_does_not_lose_message(client, monkeypatch):
    async def broken(*args, **kwargs):
        raise OSError("smtp down")

    monkeypatch.setattr(feedback_views, "send_mail", broken)
    monkeypatch.setattr(feedback_views, "ALERT_EMAIL", "admin@example.com")
    assert (await client.post("/api/feedback", json={"text": "Баг"})).status_code == 204
    assert len(await _all()) == 1


async def test_validation_and_honeypot(client):
    assert (await client.post("/api/feedback", json={"text": "   "})).status_code == 422
    assert (await client.post("/api/feedback", json={"text": "x" * 2001})).status_code == 422
    assert (await client.post("/api/feedback", json={"text": "Баг", "email": "не почта"})).status_code == 422
    assert (await client.post("/api/feedback", json={"text": "Баг", "email": ""})).status_code == 204
    r = await client.post("/api/feedback", json={"text": "spam", "website": "http://spam"})
    assert r.status_code == 204
    assert [f.text for f in await _all()] == ["Баг"]


async def test_rate_limited_per_ip(client):
    for _ in range(FEEDBACK_LIMIT):
        assert (await client.post("/api/feedback", json={"text": "Баг"})).status_code == 204
    r = await client.post("/api/feedback", json={"text": "Баг"})
    assert r.status_code == 429
    assert len(await _all()) == FEEDBACK_LIMIT
