"""Обратная связь: сохраняем сообщение и не даём одному адресу завалить ящик."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from back.models import Feedback, User

#: Сколько сообщений можно отправить с одного IP за окно.
FEEDBACK_LIMIT = 5
FEEDBACK_WINDOW = timedelta(hours=1)


class FeedbackRateLimitedError(Exception):
    pass


class FeedbackService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def submit(
        self,
        text: str,
        email: str | None,
        user: User | None,
        page: str | None,
        user_agent: str | None,
        ip: str | None,
    ) -> Feedback:
        if ip:
            recent = await self.db.scalar(
                select(func.count())
                .select_from(Feedback)
                .where(Feedback.ip == ip, Feedback.created_at > datetime.now(UTC) - FEEDBACK_WINDOW)
            )
            if recent >= FEEDBACK_LIMIT:
                raise FeedbackRateLimitedError
        item = Feedback(
            text=text,
            email=email or (user.email if user else None),
            user_id=user.id if user else None,
            page=(page or None) and page[:500],
            user_agent=(user_agent or None) and user_agent[:500],
            ip=ip,
        )
        self.db.add(item)
        await self.db.commit()
        return item
