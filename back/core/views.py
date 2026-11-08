"""Базовые классы для class-based вьюх и роутов поверх FastAPI.

Вьюха — класс с методами get/post/put/patch/delete и списком путей.
Роуты — класс со списком вьюх; он сам регистрирует их в APIRouter.

    class HealthView(View):
        paths = ("/api/health",)

        async def get(self) -> dict:
            return {"status": "ok"}

    class ApiRoutes(Routes):
        views = (HealthView,)

    app.include_router(ApiRoutes().router)

FastAPI читает сигнатуру связанного метода (без self), поэтому
path/query-параметры, Depends и response_model работают как обычно.
Экземпляр вьюхи создаётся один раз при регистрации — не храните
в нём состояние конкретного запроса.
"""

from collections.abc import Sequence
from typing import Any, ClassVar

from fastapi import APIRouter

HTTP_METHODS = ("get", "post", "put", "patch", "delete")


class View:
    #: Пути, по которым доступна вьюха (у всех путей одни и те же обработчики).
    paths: ClassVar[Sequence[str]] = ()
    #: Имя роута для url_path_for; по умолчанию — имя класса.
    name: ClassVar[str | None] = None
    #: Показывать ли в /docs. HTML-страницам там делать нечего.
    include_in_schema: ClassVar[bool] = True
    #: Доп. параметры для add_api_route (status_code, response_class, tags…).
    route_options: ClassVar[dict[str, Any]] = {}
    #: То же, но для отдельного метода — перекрывает route_options:
    #: method_options = {"post": {"status_code": 201}}
    method_options: ClassVar[dict[str, dict[str, Any]]] = {}

    @classmethod
    def handlers(cls) -> dict[str, Any]:
        """HTTP-метод → обработчик, только для реально определённых методов."""
        instance = cls()
        return {m.upper(): getattr(instance, m) for m in HTTP_METHODS if callable(getattr(cls, m, None))}


class Routes:
    prefix: ClassVar[str] = ""
    tags: ClassVar[Sequence[str]] = ()
    #: Порядок важен: первым совпавшим маршрутом будет первый зарегистрированный.
    views: ClassVar[Sequence[type[View]]] = ()

    def __init__(self) -> None:
        self.router = APIRouter(prefix=self.prefix, tags=list(self.tags))
        for view_cls in self.views:
            self.register(view_cls)

    def register(self, view_cls: type[View]) -> None:
        handlers = view_cls.handlers()
        if not handlers:
            raise TypeError(f"{view_cls.__name__}: не определён ни один из методов {HTTP_METHODS}")
        if not view_cls.paths:
            raise TypeError(f"{view_cls.__name__}: пустой список paths")
        base_name = view_cls.name or view_cls.__name__
        for i, path in enumerate(view_cls.paths):
            for method, endpoint in handlers.items():
                self.router.add_api_route(
                    path,
                    endpoint,
                    methods=[method],
                    name=base_name if i == 0 else f"{base_name}:{i}",
                    include_in_schema=view_cls.include_in_schema,
                    **(view_cls.route_options | view_cls.method_options.get(method.lower(), {})),
                )
