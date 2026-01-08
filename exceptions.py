class ApiRequestError(Exception):
    """Исключение, возникающее при ошибке запроса к API."""

    pass


class TokensNotFoundException(Exception):
    """Исключение, которое поднимается, если токены не найдены."""

    pass


class ErrorsException(Exception):
    """Исключение для обработки ошибок в программе."""

    pass
