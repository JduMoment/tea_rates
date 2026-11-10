from pydantic import Field, field_validator

from back.schemas.auth import _clean_email
from back.schemas.base import ApiModel


class FeedbackIn(ApiModel):
    text: str = Field(max_length=2000)
    #: Куда ответить; необязательно.
    email: str | None = None
    #: Путь страницы, с которой пишут (/teas/123).
    page: str | None = Field(default=None, max_length=500)
    #: Ловушка для ботов: в форме поле скрыто, человек его не заполнит.
    website: str | None = None

    @field_validator("text")
    @classmethod
    def check_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Напишите сообщение")
        return v

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str | None) -> str | None:
        return _clean_email(v) if v and v.strip() else None
