"""Логи и письма об ошибках.

Все логи — в stdout одним форматом (время, уровень, откуда): их собирает Docker,
смотреть — `docker compose -f deploy/docker-compose.prod.yml logs backend`.

Каждая запись уровня ERROR и выше (необработанное исключение в запросе, log.exception где угодно)
дополнительно уходит письмом на ALERT_EMAIL. Чтобы всплеск одной ошибки не завалил ящик:
- одинаковые ошибки склеиваются: после письма такая же молчит ALERT_REPEAT_MINUTES,
  а следующее письмо скажет, сколько раз она повторилась за это время;
- всего не больше ALERT_MAX_PER_HOUR писем в час.
Письма отправляет отдельный поток — запрос пользователя не ждёт SMTP.
"""

import logging
import logging.config
import queue
import sys
import threading
import time
import traceback
from collections.abc import Callable
from email.message import EmailMessage

from back.core.config import ALERT_EMAIL, MAIL_FROM, PUBLIC_URL, SMTP_HOST

FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"

ALERT_REPEAT_MINUTES = 10
ALERT_MAX_PER_HOUR = 20


def setup_logging() -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"plain": {"format": FORMAT}},
            "handlers": {
                "stdout": {"class": "logging.StreamHandler", "formatter": "plain", "stream": "ext://sys.stdout"},
                "alerts": {"()": AlertHandler, "level": "ERROR"},
            },
            "root": {"level": "INFO", "handlers": ["stdout", "alerts"]},
            # uvicorn настраивает свои логгеры сам — переводим их на общий формат и обработчики
            "loggers": {
                name: {"handlers": [], "propagate": True} for name in ("uvicorn", "uvicorn.error", "uvicorn.access")
            },
        }
    )


def _send_alert(subject: str, text: str) -> None:
    """Отправка в фоновом потоке. Ошибки отправки — в stderr, не в logging: иначе письмо о письме."""
    if not (ALERT_EMAIL and SMTP_HOST):
        return
    from back.core.mail import _send

    msg = EmailMessage()
    msg["From"] = MAIL_FROM
    msg["To"] = ALERT_EMAIL
    msg["Subject"] = subject
    msg.set_content(text)
    try:
        _send(msg)
    except Exception as exc:  # noqa: BLE001 — сбой почты не должен ронять приложение
        print(f"Не удалось отправить письмо об ошибке: {exc!r}", file=sys.stderr)


class _Mailer:
    """Очередь писем и поток, который их отправляет."""

    def __init__(self) -> None:
        self.queue: queue.Queue[tuple[str, str]] = queue.Queue(maxsize=100)
        self.thread: threading.Thread | None = None

    def put(self, subject: str, text: str) -> None:
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._run, name="alert-mailer", daemon=True)
            self.thread.start()
        try:
            self.queue.put_nowait((subject, text))
        except queue.Full:
            pass

    def _run(self) -> None:
        while True:
            subject, text = self.queue.get()
            _send_alert(subject, text)


_mailer = _Mailer()


class AlertHandler(logging.Handler):
    """Шлёт ERROR-записи письмом, склеивая повторы. deliver подменяется в тестах."""

    def __init__(self, deliver: Callable[[str, str], None] | None = None) -> None:
        super().__init__(level=logging.ERROR)
        self.deliver = deliver or _mailer.put
        # Свой замок не нужен: logging.Handler.handle() уже держит self.lock на время emit()
        #: ключ ошибки → (когда последний раз отправили, сколько раз повторилась с тех пор)
        self.seen: dict[str, tuple[float, int]] = {}
        self.sent: list[float] = []

    @staticmethod
    def key(record: logging.LogRecord) -> str:
        """Одна и та же ошибка — тот же тип исключения в том же месте кода (или то же сообщение)."""
        if record.exc_info and record.exc_info[1] is not None:
            exc = record.exc_info[1]
            frames = traceback.extract_tb(exc.__traceback__)
            where = f"{frames[-1].filename}:{frames[-1].lineno}" if frames else ""
            return f"{type(exc).__name__}@{where}"
        return f"{record.name}:{record.msg}"

    def emit(self, record: logging.LogRecord) -> None:
        try:
            now = time.monotonic()
            key = self.key(record)
            last, repeats = self.seen.get(key, (None, 0))
            if last is not None and now - last < ALERT_REPEAT_MINUTES * 60:
                self.seen[key] = (last, repeats + 1)
                return
            self.sent = [t for t in self.sent if now - t < 3600]
            if len(self.sent) >= ALERT_MAX_PER_HOUR:
                self.seen[key] = (last or now, repeats + 1)
                return
            self.sent.append(now)
            self.seen[key] = (now, 0)
            self.deliver(*self._compose(record, repeats))
        except Exception:  # noqa: BLE001
            self.handleError(record)

    def _compose(self, record: logging.LogRecord, repeats: int) -> tuple[str, str]:
        site = PUBLIC_URL.split("://")[-1]
        message = record.getMessage()
        if record.exc_info and record.exc_info[1] is not None:
            exc = record.exc_info[1]
            headline = f"{type(exc).__name__}: {exc}"
        else:
            headline = message.splitlines()[0] if message else record.levelname
        subject = f"[{site}] Ошибка: {headline}"[:180]
        parts = [message]
        if repeats:
            parts.append(f"С прошлого письма эта ошибка повторилась ещё {repeats} раз.")
        parts.append(f"Где: {record.name}, {record.pathname}:{record.lineno}")
        parts.append(f"Когда: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created))}")
        if record.exc_info:
            parts.append("".join(traceback.format_exception(*record.exc_info))[-8000:])
        parts.append(
            f"Одинаковые ошибки склеиваются на {ALERT_REPEAT_MINUTES} минут; "
            f"не больше {ALERT_MAX_PER_HOUR} писем в час."
        )
        return subject, "\n\n".join(parts)
