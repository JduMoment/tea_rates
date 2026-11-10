"""Необработанные ошибки: клиенту — 500 без подробностей, в лог и письмо — адрес, пользователь, трейсбек."""

import logging

import pytest

from back.core.logs import AlertHandler
from back.main import app


async def _boom() -> None:
    raise RuntimeError("тестовая поломка")


# Первым в списке: иначе адрес перехватит общий маршрут фронта /{unknown_path:path}
app.add_api_route("/api/__test_boom", _boom)
app.router.routes.insert(0, app.router.routes.pop())


@pytest.fixture
def alerts(monkeypatch):
    """Перехватываем письма: подменяем отправку у обработчика, висящего на корневом логгере."""
    sent: list[tuple[str, str]] = []
    handler = next(h for h in logging.getLogger().handlers if isinstance(h, AlertHandler))
    monkeypatch.setattr(handler, "deliver", lambda subject, text: sent.append((subject, text)))
    monkeypatch.setattr(handler, "seen", {})
    monkeypatch.setattr(handler, "sent", [])
    return sent


async def test_unhandled_error_is_500_and_alerted(client, user, alerts):
    r = await client.get("/api/__test_boom?x=1")
    assert r.status_code == 500
    assert "RuntimeError" not in r.text  # подробности — не клиенту

    assert len(alerts) == 1
    subject, text = alerts[0]
    assert "RuntimeError: тестовая поломка" in subject
    assert "GET /api/__test_boom?x=1" in text
    assert f"пользователь {user['id']}" in text
    assert "Traceback" in text


async def test_repeats_are_glued(client, alerts):
    for _ in range(5):
        assert (await client.get("/api/__test_boom")).status_code == 500
    assert len(alerts) == 1  # остальные четыре — в течение 10 минут молчат


def test_repeat_count_in_next_letter():
    sent: list[tuple[str, str]] = []
    h = AlertHandler(deliver=lambda s, t: sent.append((s, t)))
    record = logging.LogRecord("x", logging.ERROR, __file__, 1, "Сломалось", None, None)
    h.handle(record)
    h.handle(record)
    h.handle(record)
    key = h.key(record)
    last, repeats = h.seen[key]
    h.seen[key] = (last - 11 * 60, repeats)  # прошло больше 10 минут
    h.handle(record)
    assert len(sent) == 2
    assert "повторилась ещё 2 раз" in sent[1][1]


def test_hourly_cap():
    sent: list[tuple[str, str]] = []
    h = AlertHandler(deliver=lambda s, t: sent.append((s, t)))
    for i in range(30):
        h.handle(logging.LogRecord("x", logging.ERROR, __file__, 1, f"Разная ошибка {i}", None, None))
    assert len(sent) == 20
