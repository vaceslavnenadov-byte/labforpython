class RailwayError(Exception):
    """Базовое исключение."""


class NotFoundError(RailwayError):
    pass


class ValidationError(RailwayError):
    pass


class NoSeatsError(RailwayError):
    """Нет свободных мест или место занято."""


class OperationNotAllowedError(RailwayError):
    """Недопустимая операция (возврат после отправления, повторный возврат и т. п.)."""
