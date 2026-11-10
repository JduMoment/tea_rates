from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from back.core.config import PASSWORD_RESET_TTL_MINUTES, SESSION_TTL_DAYS
from back.core.security import DUMMY_HASH, NO_PASSWORD, SessionTokens, password_hasher
from back.models import PasswordReset, User, UserIdentity, UserSession
from back.services.oauth import OAuthProfile


class EmailTakenError(Exception):
    pass


class ResetLinkInvalidError(Exception):
    """Ссылка для сброса пароля неверная, устарела или уже использована."""


#: Не чаще одного письма о сбросе пароля на аккаунт за это время — чтобы форму не превращали в спам-пушку.
RESET_COOLDOWN = timedelta(minutes=2)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, name: str, email: str, password: str) -> User:
        user = User(name=name, email=email, password_hash=password_hasher.hash(password))
        self.db.add(user)
        try:
            await self.db.flush()
        except IntegrityError as exc:  # unique(email)
            await self.db.rollback()
            raise EmailTakenError from exc
        await self.db.refresh(user)
        return user

    async def authenticate(self, email: str, password: str) -> User | None:
        user = await self.db.scalar(select(User).where(User.email == email))
        # Хешируем всегда — одинаковое время ответа для существующей и несуществующей почты
        ok = password_hasher.verify(password, user.password_hash if user else DUMMY_HASH)
        return user if user and ok else None

    async def login_external(self, provider: str, profile: OAuthProfile) -> User:
        """Пользователь, вошедший через провайдера. Если его ещё нет — привязываем или создаём.

        1. Уже входил через этого провайдера — находим по (provider, subject).
        2. Есть аккаунт с той же почтой — привязываем к нему: провайдер отдаёт только
           подтверждённую почту, значит, это тот же человек.
        3. Иначе — новый пользователь без пароля.
        """
        identity = await self.db.scalar(
            select(UserIdentity).where(UserIdentity.provider == provider, UserIdentity.subject == profile.subject)
        )
        if identity:
            return identity.user

        user = await self.db.scalar(select(User).where(User.email == profile.email))
        if not user:
            user = User(name=profile.name, email=profile.email, password_hash=NO_PASSWORD)
            self.db.add(user)
            await self.db.flush()
        self.db.add(UserIdentity(provider=provider, subject=profile.subject, user_id=user.id))
        await self.db.flush()
        return user

    async def start_session(self, user: User) -> str:
        """Создаёт сессию и возвращает сырой токен для cookie."""
        token = SessionTokens.new()
        self.db.add(
            UserSession(
                token_hash=SessionTokens.digest(token),
                user_id=user.id,
                expires_at=datetime.now(UTC) + timedelta(days=SESSION_TTL_DAYS),
            )
        )
        # Заодно чистим протухшие сессии этого пользователя
        await self.db.execute(
            delete(UserSession).where(UserSession.user_id == user.id, UserSession.expires_at < datetime.now(UTC))
        )
        await self.db.commit()
        return token

    async def user_by_token(self, token: str | None) -> User | None:
        if not token:
            return None
        session = await self.db.scalar(select(UserSession).where(UserSession.token_hash == SessionTokens.digest(token)))
        if not session or session.expires_at < datetime.now(UTC):
            return None
        return session.user

    async def end_session(self, token: str | None) -> None:
        if not token:
            return
        await self.db.execute(delete(UserSession).where(UserSession.token_hash == SessionTokens.digest(token)))
        await self.db.commit()

    # ---------- восстановление пароля ----------

    async def request_reset(self, email: str) -> tuple[User, str] | None:
        """Создаёт ссылку для сброса. None — нет такого пользователя или письмо уже отправляли только что
        (снаружи эти случаи не различаем, чтобы по ответу нельзя было узнать, зарегистрирована ли почта)."""
        user = await self.db.scalar(select(User).where(User.email == email))
        if not user:
            return None
        now = datetime.now(UTC)
        recent = await self.db.scalar(
            select(PasswordReset).where(
                PasswordReset.user_id == user.id, PasswordReset.created_at > now - RESET_COOLDOWN
            )
        )
        if recent:
            return None
        token = SessionTokens.new()
        self.db.add(
            PasswordReset(
                token_hash=SessionTokens.digest(token),
                user_id=user.id,
                created_at=now,
                expires_at=now + timedelta(minutes=PASSWORD_RESET_TTL_MINUTES),
            )
        )
        await self.db.commit()
        return user, token

    async def reset_password(self, token: str, password: str) -> User:
        """Меняет пароль по ссылке и завершает все сессии пользователя (вдруг доступ был у кого-то ещё)."""
        reset = await self.db.get(PasswordReset, SessionTokens.digest(token))
        now = datetime.now(UTC)
        if not reset or reset.used_at or reset.expires_at < now:
            raise ResetLinkInvalidError
        user = await self.db.get(User, reset.user_id)
        user.password_hash = password_hasher.hash(password)
        reset.used_at = now
        await self.db.execute(delete(UserSession).where(UserSession.user_id == user.id))
        await self.db.commit()
        return user
