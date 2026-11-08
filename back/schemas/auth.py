import re
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _clean_email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 254 or not EMAIL_RE.match(value):
        raise ValueError("Проверьте адрес почты")
    return value


class RegisterIn(BaseModel):
    name: str = Field(max_length=64)
    email: str
    password: str = Field(max_length=128)

    @field_validator("name")
    @classmethod
    def check_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Имя слишком короткое")
        return v

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return _clean_email(v)

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Пароль — минимум 6 символов")
        return v


class LoginIn(BaseModel):
    email: str
    password: str = Field(max_length=128)

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return v.strip().lower()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    joined: date

    @classmethod
    def from_user(cls, user) -> "UserOut":
        return cls(id=user.id, name=user.name, email=user.email, joined=user.created_at.date())
