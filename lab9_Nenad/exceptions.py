class HotelError(Exception):
    """Базовое исключение приложения."""


class ProtocolError(HotelError):
    """Нарушение формата сообщения прикладного протокола."""


class RoomNotFoundError(HotelError):
    def __init__(self, room_id: int):
        super().__init__(f"Room {room_id} not found")


class ValidationError(HotelError):
    """Некорректные значения параметров."""


class ConflictError(HotelError):
    """Операция противоречит текущему состоянию (номер занят, дубликат и т. п.)."""
