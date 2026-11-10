from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from back.core.db import Base


class Feedback(Base):
    """Сообщение в обратную связь («нашёл баг», «есть идея»). Писать может и гость."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    #: Куда ответить: введённая почта или почта вошедшего пользователя.
    email: Mapped[str | None] = mapped_column(String(254))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    #: Страница, с которой написали, и браузер — помогают воспроизвести баг.
    page: Mapped[str | None] = mapped_column(String(500))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    #: Для ограничения частоты отправки.
    ip: Mapped[str | None] = mapped_column(String(45), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
