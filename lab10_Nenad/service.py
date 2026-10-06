"""Бизнес-логика работы с поездами."""

from dataclasses import asdict

from exceptions import ConflictError, TrainNotFoundError, ValidationError
from models import Train, TrainStatus
from repository import TrainRepository
from schemas import validate_train

SORT_FIELDS = {"price", "departure_time", "free_seats", "number"}


class TrainService:
    def __init__(self, repository: TrainRepository) -> None:
        self.repository = repository

    def _check_unique(self, number: str, departure_time: str, exclude_id: int | None = None) -> None:
        for t in self.repository.get_all():
            if t.number == number and t.departure_time == departure_time and t.id != exclude_id:
                raise ConflictError(f"Train {number} at {departure_time} already exists")

    def get_trains(self, filters: dict | None = None, sort: str | None = None, order: str = "asc") -> list[Train]:
        filters = filters or {}
        trains = self.repository.get_all()
        if filters.get("from"):
            trains = [t for t in trains if filters["from"].lower() in t.departure_station.lower()]
        if filters.get("to"):
            trains = [t for t in trains if filters["to"].lower() in t.arrival_station.lower()]
        if filters.get("status"):
            trains = [t for t in trains if t.status.value == filters["status"]]
        if filters.get("date"):
            trains = [t for t in trains if t.departure_time.startswith(filters["date"])]
        if filters.get("min_price") is not None:
            trains = [t for t in trains if t.price >= filters["min_price"]]
        if filters.get("max_price") is not None:
            trains = [t for t in trains if t.price <= filters["max_price"]]
        if sort:
            if sort not in SORT_FIELDS:
                raise ValidationError(f"Sort field must be one of {sorted(SORT_FIELDS)}")
            if order not in ("asc", "desc"):
                raise ValidationError("Order must be 'asc' or 'desc'")
            trains.sort(key=lambda t: getattr(t, sort), reverse=order == "desc")
        return trains

    def get_train(self, train_id: int) -> Train:
        train = self.repository.get_by_id(train_id)
        if train is None:
            raise TrainNotFoundError(train_id)
        return train

    def create_train(self, data: dict) -> Train:
        clean = validate_train(data)
        self._check_unique(clean["number"], clean["departure_time"])
        clean.setdefault("booked_seats", 0)
        clean.setdefault("status", TrainStatus.SCHEDULED)
        return self.repository.create(Train(id=0, **clean))

    def replace_train(self, train_id: int, data: dict) -> Train:
        self.get_train(train_id)
        clean = validate_train(data)
        self._check_unique(clean["number"], clean["departure_time"], exclude_id=train_id)
        clean.setdefault("booked_seats", 0)
        clean.setdefault("status", TrainStatus.SCHEDULED)
        return self.repository.update(Train(id=train_id, **clean))

    def patch_train(self, train_id: int, data: dict) -> Train:
        train = self.get_train(train_id)
        current = {k: v for k, v in asdict(train).items() if k != "id"}
        current["status"] = train.status.value
        clean = validate_train(data, partial=True, current=current)
        for key, value in clean.items():
            setattr(train, key, value)
        if "number" in clean or "departure_time" in clean:
            self._check_unique(train.number, train.departure_time, exclude_id=train_id)
        return self.repository.update(train)

    def delete_train(self, train_id: int) -> None:
        train = self.get_train(train_id)
        if train.booked_seats > 0 and train.status != TrainStatus.CANCELLED:
            raise ConflictError("Cannot delete a train with sold tickets; cancel it first")
        self.repository.delete(train_id)

    # ---------- специализированная операция варианта 10: свободные места ----------
    def trains_with_free_seats(self, min_seats: int = 1, filters: dict | None = None) -> list[dict]:
        if min_seats < 1:
            raise ValidationError("min_seats must be >= 1")
        result = []
        for t in self.get_trains(filters, sort="departure_time"):
            if t.status == TrainStatus.SCHEDULED and t.free_seats >= min_seats:
                result.append({"id": t.id, "number": t.number, "route": f"{t.departure_station} - {t.arrival_station}",
                               "departure_time": t.departure_time, "free_seats": t.free_seats,
                               "total_seats": t.total_seats, "price": t.price})
        return result

    def book_seats(self, train_id: int, count: int) -> Train:
        if count < 1:
            raise ValidationError("count must be >= 1")
        train = self.get_train(train_id)
        if train.status != TrainStatus.SCHEDULED:
            raise ConflictError(f"Booking is closed: train is {train.status.value}")
        if train.free_seats < count:
            raise ConflictError(f"Only {train.free_seats} free seats left")
        train.booked_seats += count
        return self.repository.update(train)


def seed(service: TrainService) -> None:
    demo = [
        ("001А", "Москва", "Санкт-Петербург", "2026-10-10T23:55", "2026-10-11T07:55", 12, 36, 400, 3200),
        ("752А", "Москва", "Санкт-Петербург", "2026-10-10T06:50", "2026-10-10T10:45", 10, 60, 600, 4100),
        ("104В", "Москва", "Казань", "2026-10-11T21:20", "2026-10-12T08:50", 14, 36, 250, 2400),
        ("026Ч", "Москва", "Сочи", "2026-10-12T12:00", "2026-10-13T17:30", 16, 36, 576, 5600),
        ("002А", "Санкт-Петербург", "Москва", "2026-10-12T23:55", "2026-10-13T07:55", 12, 36, 120, 3200),
        ("015Е", "Екатеринбург", "Москва", "2026-10-13T08:10", "2026-10-14T09:20", 15, 36, 300, 4800),
    ]
    for number, dep, arr, dep_t, arr_t, wagons, seats, booked, price in demo:
        service.create_train({"number": number, "departure_station": dep, "arrival_station": arr,
                              "departure_time": dep_t, "arrival_time": arr_t, "wagons": wagons,
                              "seats_per_wagon": seats, "booked_seats": booked, "price": price})
