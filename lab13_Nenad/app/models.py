"""Модель документа «поезд» и проверка входных данных."""

from dataclasses import asdict, dataclass, field
from datetime import datetime

STATUSES = ("scheduled", "boarding", "departed", "arrived", "cancelled")
WAGON_TYPES = {"seated": 60, "coupe": 36, "sv": 18}


class ValidationError(ValueError):
    pass


@dataclass
class Stop:
    station: str
    city: str
    arrival: str | None
    departure: str | None


@dataclass
class Wagon:
    number: int
    type: str
    seats: int
    booked: list[int] = field(default_factory=list)

    @property
    def free(self) -> int:
        return self.seats - len(self.booked)


@dataclass
class Train:
    number: str
    name: str
    category: str                      # скорый / пассажирский / высокоскоростной
    stops: list[Stop]
    wagons: list[Wagon]
    base_price: float
    status: str = "scheduled"
    _id: int | None = None

    def to_document(self) -> dict:
        """Документ MongoDB: маршрут — вложенный объект, станции и вагоны — массивы."""
        doc = asdict(self)
        if doc["_id"] is None:
            del doc["_id"]
        doc["route"] = {"from": {"station": self.stops[0].station, "city": self.stops[0].city},
                        "to": {"station": self.stops[-1].station, "city": self.stops[-1].city}}
        doc["departure_time"] = datetime.fromisoformat(self.stops[0].departure)
        doc["arrival_time"] = datetime.fromisoformat(self.stops[-1].arrival)
        doc["cities"] = [s.city for s in self.stops]
        doc["total_seats"] = sum(w.seats for w in self.wagons)
        doc["free_seats"] = sum(w.free for w in self.wagons)
        doc["version"] = 0
        return doc


def validate_train(data: dict) -> Train:
    try:
        stops = [Stop(**s) for s in data["stops"]]
        wagons = [Wagon(w["number"], w["type"], w.get("seats", WAGON_TYPES.get(w["type"], 0)), w.get("booked", []))
                  for w in data["wagons"]]
        train = Train(str(data["number"]).strip(), data["name"], data["category"], stops, wagons,
                      float(data["base_price"]), data.get("status", "scheduled"))
    except (KeyError, TypeError) as error:
        raise ValidationError(f"Некорректная структура документа: {error}") from None
    if not train.number:
        raise ValidationError("Номер поезда обязателен")
    if len(train.stops) < 2:
        raise ValidationError("Маршрут должен содержать минимум 2 станции")
    if train.base_price <= 0:
        raise ValidationError("Цена должна быть положительной")
    if train.status not in STATUSES:
        raise ValidationError(f"Статус должен быть одним из {STATUSES}")
    for wagon in train.wagons:
        if wagon.type not in WAGON_TYPES:
            raise ValidationError(f"Неизвестный тип вагона: {wagon.type}")
    try:
        departure = datetime.fromisoformat(train.stops[0].departure)
        arrival = datetime.fromisoformat(train.stops[-1].arrival)
    except (TypeError, ValueError):
        raise ValidationError("Время должно быть в формате ISO: 2026-10-10T23:55") from None
    if arrival <= departure:
        raise ValidationError("Прибытие должно быть позже отправления")
    return train
