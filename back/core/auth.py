"""Зависимости и работа с cookie сессии."""

import base64
import json
from dataclasses import asdict, dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status

from back.core.config import COOKIE_SECURE, SESSION_COOKIE, SESSION_TTL_DAYS
from back.core.db import DbSession
from back.models import User
from back.services.auth import AuthService


class SessionCookie:
    @staticmethod
    def read(request: Request) -> str | None:
        return request.cookies.get(SESSION_COOKIE)

    @staticmethod
    def set(response: Response, token: str) -> None:
        response.set_cookie(
            SESSION_COOKIE,
            token,
            max_age=SESSION_TTL_DAYS * 24 * 3600,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite="lax",
            path="/",
        )

    @staticmethod
    def clear(response: Response) -> None:
        response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, secure=COOKIE_SECURE, samesite="lax")


@dataclass(frozen=True)
class OAuthState:
    provider: str
    #: Случайная строка; провайдер вернёт её в ?state= — так проверяем, что вход начали мы (CSRF).
    state: str
    #: PKCE verifier — без него украденный code бесполезен.
    verifier: str
    #: Куда вернуть пользователя после входа (относительный путь).
    next: str


class OAuthStateCookie:
    """Короткоживущая cookie на время входа через провайдера (от /start до /callback)."""

    name = "tea_oauth"
    path = "/api/auth/oauth"
    max_age = 10 * 60

    @classmethod
    def set(cls, response: Response, value: OAuthState) -> None:
        raw = base64.urlsafe_b64encode(json.dumps(asdict(value)).encode()).decode()
        # lax: cookie придёт на callback, ведь это переход верхнего уровня с oauth.yandex.ru
        response.set_cookie(
            cls.name, raw, max_age=cls.max_age, httponly=True, secure=COOKIE_SECURE, samesite="lax", path=cls.path
        )

    @classmethod
    def read(cls, request: Request) -> OAuthState | None:
        raw = request.cookies.get(cls.name)
        if not raw:
            return None
        try:
            return OAuthState(**json.loads(base64.urlsafe_b64decode(raw)))
        except (ValueError, TypeError):
            return None

    @classmethod
    def clear(cls, response: Response) -> None:
        response.delete_cookie(cls.name, path=cls.path, httponly=True, secure=COOKIE_SECURE, samesite="lax")


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(db)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_user(request: Request, auth: AuthServiceDep) -> User:
    user = await auth.user_by_token(SessionCookie.read(request))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Нужно войти")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_optional_user(request: Request, auth: AuthServiceDep) -> User | None:
    """Текущий пользователь или None — для публичных страниц, где вошедшим показываем чуть больше."""
    return await auth.user_by_token(SessionCookie.read(request))


OptionalUser = Annotated[User | None, Depends(get_optional_user)]
