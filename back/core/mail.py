"""Отправка писем по SMTP. Без настроенного SMTP_HOST письмо пишется в лог — так удобно разрабатывать."""

import logging
import smtplib
import ssl
from email.message import EmailMessage

from starlette.concurrency import run_in_threadpool

from back.core.config import MAIL_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_SECURITY, SMTP_USER

log = logging.getLogger(__name__)


def _send(msg: EmailMessage) -> None:
    context = ssl.create_default_context()
    if SMTP_SECURITY == "ssl":
        server: smtplib.SMTP = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=15)
    else:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
        server.starttls(context=context)
    with server:
        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)


async def send_mail(to: str, subject: str, text: str, reply_to: str | None = None) -> None:
    msg = EmailMessage()
    msg["From"] = MAIL_FROM
    msg["To"] = to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(text)
    if not SMTP_HOST:
        log.warning("SMTP не настроен — письмо не отправлено.\nКому: %s\nТема: %s\n\n%s", to, subject, text)
        return
    await run_in_threadpool(_send, msg)
