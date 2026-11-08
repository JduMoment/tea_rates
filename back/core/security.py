"""Хеширование паролей и токены сессий на стандартной библиотеке (без внешних зависимостей)."""

import base64
import hashlib
import hmac
import secrets


class PasswordHasher:
    """scrypt с солью. Формат хранения: scrypt$n$r$p$<salt b64>$<hash b64>."""

    n = 2**14
    r = 8
    p = 1
    dklen = 32
    salt_bytes = 16

    def hash(self, password: str) -> str:
        salt = secrets.token_bytes(self.salt_bytes)
        digest = self._derive(password, salt, self.n, self.r, self.p)
        return "$".join(["scrypt", str(self.n), str(self.r), str(self.p), _b64(salt), _b64(digest)])

    def verify(self, password: str, stored: str) -> bool:
        try:
            algo, n, r, p, salt, digest = stored.split("$")
            if algo != "scrypt":
                return False
            expected = base64.b64decode(digest)
            actual = self._derive(password, base64.b64decode(salt), int(n), int(r), int(p))
        except ValueError:
            return False
        return hmac.compare_digest(actual, expected)

    def _derive(self, password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
        return hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, dklen=self.dklen, maxmem=64 * 1024 * 1024)


class SessionTokens:
    @staticmethod
    def new() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def digest(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()


class Pkce:
    """PKCE (RFC 7636): verifier храним у себя, провайдеру отдаём только его хеш."""

    @staticmethod
    def new_verifier() -> str:
        return secrets.token_urlsafe(48)  # 64 символа, в пределах 43..128

    @staticmethod
    def challenge(verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


password_hasher = PasswordHasher()
#: «Пароля нет» — у тех, кто вошёл через Яндекс, и у демо-пользователей из сида.
#: Не парсится как scrypt-хеш, поэтому verify() для него всегда False.
NO_PASSWORD = "!"
#: Хеш-заглушка: проверяем пароль даже для несуществующей почты, чтобы по времени ответа
#: нельзя было понять, зарегистрирован ли адрес.
DUMMY_HASH = password_hasher.hash(secrets.token_urlsafe(16))
