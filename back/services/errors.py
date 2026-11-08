class NotFoundError(Exception):
    """Объект не найден (или чужой — снаружи это не различаем). Превращается в HTTP 404 в main.py."""

    message = "Не найдено"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)


class TeaNotFoundError(NotFoundError):
    message = "Чай не найден"


class ShopNotFoundError(NotFoundError):
    message = "Магазин не найден"


class CategoryNotFoundError(NotFoundError):
    message = "Такого вида чая нет"


class ReviewNotFoundError(NotFoundError):
    message = "Отзыв не найден"


class DiaryEntryNotFoundError(NotFoundError):
    message = "Запись не найдена"


class UserNotFoundError(NotFoundError):
    message = "Пользователь не найден"


class OfferNotFoundError(NotFoundError):
    message = "Этот чай не продаётся в этом магазине"


class ConflictError(Exception):
    """Такой объект уже есть. Превращается в HTTP 409 в main.py."""

    message = "Уже существует"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)


class TeaExistsError(ConflictError):
    message = "Такой чай уже есть в каталоге"


class OfferExistsError(ConflictError):
    message = "Этот чай уже добавлен в этот магазин"


class ForbiddenError(Exception):
    """Объект виден, но менять его нельзя. Превращается в HTTP 403 в main.py."""

    message = "Недостаточно прав"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)


class TeaLockedError(ForbiddenError):
    message = "Менять и удалять чай может только тот, кто его добавил, и только пока на него нет чужих отзывов"


class LastOfferError(ForbiddenError):
    message = "Это единственный магазин с этим чаем — удалите сам чай"


class OfferLockedError(ForbiddenError):
    message = "Менять и убирать магазин у чая может только тот, кто его добавил, и только пока нет чужих отзывов на покупку там"


class OwnReviewVoteError(ForbiddenError):
    message = "Свой отзыв отметить полезным нельзя"


class FollowSelfError(ForbiddenError):
    message = "На себя подписаться нельзя"
