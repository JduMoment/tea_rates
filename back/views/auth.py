import hmac
import logging
from typing import ClassVar
from urllib.parse import urlencode

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from back.core.auth import AuthServiceDep, CurrentUser, OAuthState, OAuthStateCookie, SessionCookie
from back.core.config import PASSWORD_RESET_TTL_MINUTES, PUBLIC_URL
from back.core.mail import send_mail
from back.core.security import Pkce, SessionTokens
from back.core.views import View
from back.schemas.auth import ForgotPasswordIn, LoginIn, RegisterIn, ResetPasswordIn, UserOut
from back.services.auth import EmailTakenError, ResetLinkInvalidError
from back.services.oauth import PROVIDERS, OAuthError, YandexOAuth

log = logging.getLogger(__name__)


class RegisterView(View):
    paths = ("/register",)
    route_options: ClassVar[dict] = {"status_code": status.HTTP_201_CREATED}

    async def post(self, data: RegisterIn, response: Response, auth: AuthServiceDep) -> UserOut:
        try:
            user = await auth.register(data.name, data.email, data.password)
        except EmailTakenError:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Пользователь с такой почтой уже есть") from None
        SessionCookie.set(response, await auth.start_session(user))
        return UserOut.from_user(user)


class LoginView(View):
    paths = ("/login",)

    async def post(self, data: LoginIn, response: Response, auth: AuthServiceDep) -> UserOut:
        user = await auth.authenticate(data.email, data.password)
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Неверная почта или пароль")
        SessionCookie.set(response, await auth.start_session(user))
        return UserOut.from_user(user)


class LogoutView(View):
    paths = ("/logout",)
    route_options: ClassVar[dict] = {"status_code": status.HTTP_204_NO_CONTENT}

    async def post(self, request: Request, response: Response, auth: AuthServiceDep) -> None:
        await auth.end_session(SessionCookie.read(request))
        SessionCookie.clear(response)


class MeView(View):
    paths = ("/me",)

    async def get(self, user: CurrentUser) -> UserOut:
        return UserOut.from_user(user)


def _safe_next(path: str) -> str:
    """Только относительный путь на нашем сайте — иначе ?next= можно использовать для редиректа на чужой."""
    if not path.startswith("/") or path.startswith(("//", "/\\", "/api/")):
        return "/"
    return path


def _provider(name: str) -> YandexOAuth:
    provider = PROVIDERS.get(name)
    if not provider:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Неизвестный способ входа")
    return provider


def _login_failed(code: str) -> RedirectResponse:
    """Назад на страницу входа; фронт покажет текст ошибки по коду."""
    response = RedirectResponse(f"/login?{urlencode({'oauth_error': code})}", status.HTTP_303_SEE_OTHER)
    OAuthStateCookie.clear(response)
    return response


class OAuthStartView(View):
    """Кнопка «Войти с Яндекс ID» ведёт сюда, а отсюда — на страницу согласия провайдера."""

    paths = ("/oauth/{provider}/start",)
    include_in_schema = False

    async def get(self, provider: str, next: str = "/") -> RedirectResponse:
        client = _provider(provider)
        if not client.configured:
            return _login_failed("unavailable")
        saved = OAuthState(
            provider=client.name, state=SessionTokens.new(), verifier=Pkce.new_verifier(), next=_safe_next(next)
        )
        response = RedirectResponse(
            client.authorize_redirect(saved.state, Pkce.challenge(saved.verifier)), status.HTTP_303_SEE_OTHER
        )
        OAuthStateCookie.set(response, saved)
        return response


class OAuthCallbackView(View):
    """Сюда провайдер возвращает пользователя: ?code=…&state=… или ?error=…&state=…"""

    paths = ("/oauth/{provider}/callback",)
    include_in_schema = False

    async def get(
        self,
        provider: str,
        request: Request,
        auth: AuthServiceDep,
        code: str | None = None,
        state: str | None = None,
        error: str | None = None,
    ) -> RedirectResponse:
        client = _provider(provider)
        saved = OAuthStateCookie.read(request)
        if not saved or saved.provider != client.name or not state or not hmac.compare_digest(state, saved.state):
            return _login_failed("state")
        if error or not code:
            return _login_failed("denied" if error == "access_denied" else "provider")
        try:
            profile = await client.fetch_profile(code, saved.verifier)
        except OAuthError as exc:
            log.warning("Вход через %s не удался: %s", client.name, exc)
            return _login_failed(exc.code)

        user = await auth.login_external(client.name, profile)
        response = RedirectResponse(saved.next, status.HTTP_303_SEE_OTHER)
        SessionCookie.set(response, await auth.start_session(user))
        OAuthStateCookie.clear(response)
        return response


class ForgotPasswordView(View):
    """Письмо со ссылкой для смены пароля. Ответ всегда 204 — не подсказываем, есть ли такая почта."""

    paths = ("/password/forgot",)
    route_options: ClassVar[dict] = {"status_code": status.HTTP_204_NO_CONTENT}

    async def post(self, data: ForgotPasswordIn, auth: AuthServiceDep) -> None:
        found = await auth.request_reset(data.email)
        if not found:
            return
        user, token = found
        link = f"{PUBLIC_URL}/reset-password?{urlencode({'token': token})}"
        await send_mail(
            user.email,
            "Смена пароля — 5 листов",
            f"Здравствуйте, {user.name}!\n\n"
            f"Чтобы задать новый пароль, откройте ссылку:\n{link}\n\n"
            f"Ссылка действует {PASSWORD_RESET_TTL_MINUTES} минут и сработает один раз.\n"
            "Если вы не просили сменить пароль — просто проигнорируйте это письмо.\n",
        )


class ResetPasswordView(View):
    """Новый пароль по ссылке из письма. Все прежние сессии завершаются, текущая — входит заново."""

    paths = ("/password/reset",)

    async def post(self, data: ResetPasswordIn, response: Response, auth: AuthServiceDep) -> UserOut:
        try:
            user = await auth.reset_password(data.token, data.password)
        except ResetLinkInvalidError:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="Ссылка устарела или уже использована — запросите новую"
            ) from None
        SessionCookie.set(response, await auth.start_session(user))
        return UserOut.from_user(user)
