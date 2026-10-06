"""Пользовательские исключения."""


class RailwayError(Exception):
    """Базовое исключение предметной области."""


class EntityNotFoundError(RailwayError):
    def __init__(self, entity: str, entity_id: int):
        super().__init__(f"{entity} с id={entity_id} не найден")


class SeatUnavailableError(RailwayError):
    """Место занято или не существует."""


class InvalidStatusError(RailwayError):
    """Недопустимое изменение состояния билета."""


class ValidationError(RailwayError):
    """Некорректное значение параметра."""
