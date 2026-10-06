"""Валидация входных данных (без сторонних библиотек)."""

from datetime import datetime

from exceptions import ValidationError
from models import TrainStatus

FIELDS = {
    "number": str,
    "departure_station": str,
    "arrival_station": str,
    "departure_time": str,
    "arrival_time": str,
    "wagons": int,
    "seats_per_wagon": int,
    "booked_seats": int,
    "price": float,
    "status": str,
}
REQUIRED = set(FIELDS) - {"booked_seats", "status"}


def _parse_time(value: str, field: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValidationError(f"Field '{field}' must be ISO datetime, e.g. 2026-10-10T23:55") from None


def validate_train(data, partial: bool = False, current: dict | None = None) -> dict:
    """Проверяет тело запроса. partial=True — для PATCH (обязательных полей нет)."""
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object")
    unknown = set(data) - set(FIELDS)
    if unknown:
        raise ValidationError(f"Unknown fields: {', '.join(sorted(unknown))}")
    if not partial:
        missing = REQUIRED - set(data)
        if missing:
            raise ValidationError(f"Missing fields: {', '.join(sorted(missing))}")

    clean = {}
    for field, value in data.items():
        expected = FIELDS[field]
        if expected is str:
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"Field '{field}' must be a non-empty string")
            clean[field] = value.strip()
        else:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValidationError(f"Field '{field}' must be a number")
            if expected is int and int(value) != value:
                raise ValidationError(f"Field '{field}' must be an integer")
            clean[field] = expected(value)

    merged = {**(current or {}), **clean}
    if "status" in clean:
        try:
            clean["status"] = TrainStatus(clean["status"])
        except ValueError:
            raise ValidationError(f"Status must be one of {[s.value for s in TrainStatus]}") from None
    for field in ("wagons", "seats_per_wagon"):
        if field in merged and merged[field] <= 0:
            raise ValidationError(f"Field '{field}' must be > 0")
    if "price" in merged and merged["price"] <= 0:
        raise ValidationError("Field 'price' must be > 0")
    if merged.get("booked_seats", 0) < 0:
        raise ValidationError("Field 'booked_seats' must be >= 0")
    if {"wagons", "seats_per_wagon"} <= merged.keys():
        if merged.get("booked_seats", 0) > merged["wagons"] * merged["seats_per_wagon"]:
            raise ValidationError("booked_seats exceeds total seats")
    if {"departure_time", "arrival_time"} <= merged.keys():
        dep = _parse_time(merged["departure_time"], "departure_time")
        arr = _parse_time(merged["arrival_time"], "arrival_time")
        if arr <= dep:
            raise ValidationError("arrival_time must be later than departure_time")
    if merged.get("departure_station") and merged.get("departure_station") == merged.get("arrival_station"):
        raise ValidationError("Departure and arrival stations must differ")
    return clean
