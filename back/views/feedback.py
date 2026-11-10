import logging
from typing import ClassVar

from fastapi import HTTPException, Request, status

from back.core.auth import OptionalUser
from back.core.config import ALERT_EMAIL, PUBLIC_URL
from back.core.deps import FeedbackDep
from back.core.mail import send_mail
from back.core.views import View
from back.schemas.feedback import FeedbackIn
from back.services.feedback import FeedbackRateLimitedError

log = logging.getLogger(__name__)


class FeedbackView(View):
    """Сообщение о баге или идея. Сохраняется в БД и уходит письмом на ALERT_EMAIL."""

    paths = ("/feedback",)
    route_options: ClassVar[dict] = {"status_code": status.HTTP_204_NO_CONTENT}

    async def post(self, data: FeedbackIn, request: Request, user: OptionalUser, feedback: FeedbackDep) -> None:
        if data.website:  # бот заполнил скрытое поле — делаем вид, что всё хорошо
            return
        try:
            item = await feedback.submit(
                text=data.text,
                email=data.email,
                user=user,
                page=data.page,
                user_agent=request.headers.get("user-agent"),
                ip=request.client.host if request.client else None,
            )
        except FeedbackRateLimitedError:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS, detail="Слишком много сообщений подряд — попробуйте через час"
            ) from None

        log.info("Обратная связь #%s: %s", item.id, item.text[:200])
        if not ALERT_EMAIL:
            return
        who = f"{user.name} (id {user.id})" if user else "гость"
        page = f"{PUBLIC_URL}{item.page}" if item.page and item.page.startswith("/") else item.page or "—"
        try:
            await send_mail(
                ALERT_EMAIL,
                f"Обратная связь #{item.id} — 5 листов",
                f"{item.text}\n\n"
                f"---\nОт: {who}\nПочта для ответа: {item.email or '—'}\n"
                f"Страница: {page}\nБраузер: {item.user_agent or '—'}\n",
                reply_to=item.email,
            )
        except Exception:  # сообщение уже в базе — пользователю ошибку не показываем
            log.exception("Не удалось отправить письмо с обратной связью #%s", item.id)
