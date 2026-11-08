"""Вход через внешних провайдеров: OAuth 2.0 authorization code + PKCE. Пока только Яндекс ID.

Схема:
1. /api/auth/oauth/yandex/start — запоминаем state и PKCE verifier в cookie, уводим на oauth.yandex.ru.
2. Пользователь соглашается, Яндекс возвращает его на /api/auth/oauth/yandex/callback?code=…&state=….
3. Бэкенд меняет code на токен (секрет приложения есть только у нас), берёт профиль с login.yandex.ru
   и заводит обычную сессию в cookie — дальше всё как при входе по паролю.
"""

from dataclasses import dataclass
from typing import ClassVar
from urllib.parse import urlencode

import httpx

from back.core.config import PUBLIC_URL, YANDEX_CLIENT_ID, YANDEX_CLIENT_SECRET

HTTP_TIMEOUT = 10.0


class OAuthError(Exception):
    """Вход не удался. code уходит на фронт в ?oauth_error= и превращается там в текст."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code


@dataclass(frozen=True)
class OAuthProfile:
    #: Постоянный id пользователя у провайдера.
    subject: str
    #: Подтверждённая почта, в нижнем регистре.
    email: str
    name: str


class YandexOAuth:
    name: ClassVar[str] = "yandex"
    authorize_url: ClassVar[str] = "https://oauth.yandex.ru/authorize"
    token_url: ClassVar[str] = "https://oauth.yandex.ru/token"
    info_url: ClassVar[str] = "https://login.yandex.ru/info"

    def __init__(self, client_id: str, client_secret: str, public_url: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = f"{public_url}/api/auth/oauth/{self.name}/callback"

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def authorize_redirect(self, state: str, code_challenge: str) -> str:
        """Куда отправить браузер. Доступы (login:info, login:email) берутся из настроек приложения."""
        query = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.authorize_url}?{urlencode(query)}"

    async def fetch_profile(self, code: str, code_verifier: str) -> OAuthProfile:
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                token = await self._exchange_code(client, code, code_verifier)
                info = await self._user_info(client, token)
        except httpx.HTTPError as exc:
            raise OAuthError("provider", f"Яндекс недоступен: {exc!r}") from exc
        return self._profile(info)

    async def _exchange_code(self, client: httpx.AsyncClient, code: str, code_verifier: str) -> str:
        resp = await client.post(
            self.token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        body = _json(resp)
        if resp.status_code != 200 or not body.get("access_token"):
            raise OAuthError("provider", f"Яндекс не выдал токен: {resp.status_code} {body.get('error')}")
        return body["access_token"]

    async def _user_info(self, client: httpx.AsyncClient, token: str) -> dict:
        resp = await client.get(self.info_url, params={"format": "json"}, headers={"Authorization": f"OAuth {token}"})
        body = _json(resp)
        if resp.status_code != 200 or not body.get("id"):
            raise OAuthError("provider", f"Яндекс не отдал профиль: {resp.status_code}")
        return body

    @staticmethod
    def _profile(info: dict) -> OAuthProfile:
        email = (info.get("default_email") or next(iter(info.get("emails") or []), "")).strip().lower()
        if not email:
            raise OAuthError("no_email")
        login = (info.get("login") or "").strip()
        name = next(
            (n.strip() for n in (info.get("display_name"), info.get("real_name"), login) if n and len(n.strip()) >= 2),
            email.split("@")[0],
        )
        return OAuthProfile(subject=str(info["id"]), email=email, name=name[:64])


def _json(resp: httpx.Response) -> dict:
    try:
        body = resp.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


#: Подключённые провайдеры: имя в URL → клиент.
PROVIDERS: dict[str, YandexOAuth] = {
    YandexOAuth.name: YandexOAuth(YANDEX_CLIENT_ID, YANDEX_CLIENT_SECRET, PUBLIC_URL),
}
