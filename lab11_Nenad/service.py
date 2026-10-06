"""Бизнес-логика + кэширование (cache-aside) в Redis."""

import sqlite3

from cache import RedisCache
from exceptions import ConflictError, NotFoundError, ValidationError
from repository import SORT_COLUMNS, TicketRepository, TrainRepository

STATUSES = {"scheduled", "boarding", "departed", "cancelled"}
COEFFICIENTS = {"seated": 1.0, "coupe": 1.8, "sv": 3.0}
SCHEDULE_TTL = 60   # «состояние расписания» кэшируется на 60 секунд
TRAIN_TTL = 60


class RailwayService:
    def __init__(self, trains: TrainRepository, tickets: TicketRepository, cache: RedisCache) -> None:
        self.trains = trains
        self.tickets = tickets
        self.cache = cache

    # ---------- проверки ----------
    @staticmethod
    def _validate(data: dict, partial: bool) -> dict:
        if not isinstance(data, dict):
            raise ValidationError("Body must be a JSON object")
        unknown = set(data) - {"number", "name", "base_price", "status"}
        if unknown:
            raise ValidationError(f"Unknown fields: {sorted(unknown)}")
        if not partial and not {"number", "base_price"} <= data.keys():
            raise ValidationError("Fields 'number' and 'base_price' are required")
        if "number" in data and (not isinstance(data["number"], str) or not data["number"].strip()):
            raise ValidationError("number must be a non-empty string")
        if "base_price" in data:
            price = data["base_price"]
            if isinstance(price, bool) or not isinstance(price, (int, float)) or price <= 0:
                raise ValidationError("base_price must be a positive number")
        if "status" in data and data["status"] not in STATUSES:
            raise ValidationError(f"status must be one of {sorted(STATUSES)}")
        return data

    def _invalidate(self, train_id: int) -> None:
        self.cache.delete(f"train:{train_id}", f"train:{train_id}:schedule")

    # ---------- поезда ----------
    def list_trains(self, status=None, min_price=None, max_price=None, sort="number", order="asc"):
        if sort not in SORT_COLUMNS:
            raise ValidationError(f"sort must be one of {sorted(SORT_COLUMNS)}")
        if order not in ("asc", "desc"):
            raise ValidationError("order must be asc or desc")
        return self.trains.get_all(status, min_price, max_price, sort, order)

    def get_train(self, train_id: int) -> dict:
        """Cache-aside: Redis → (промах) SQLite → Redis."""
        key = f"train:{train_id}"
        cached = self.cache.get_json(key)
        if cached is not None:
            cached["source"] = "cache"
            return cached
        train = self.trains.get_by_id(train_id)
        if train is None:
            raise NotFoundError(f"Train {train_id} not found")
        train["wagons"] = self.trains.wagons(train_id)
        self.cache.set_json(key, train, TRAIN_TTL)
        self.cache.incr_view(train["number"])
        train["source"] = "database"
        return train

    def create_train(self, data: dict) -> dict:
        self._validate(data, partial=False)
        try:
            train_id = self.trains.create(data)
        except sqlite3.IntegrityError:
            raise ConflictError(f"Train {data['number']} already exists") from None
        return self.get_train(train_id)

    def update_train(self, train_id: int, data: dict, partial: bool) -> dict:
        if self.trains.get_by_id(train_id) is None:
            raise NotFoundError(f"Train {train_id} not found")
        self._validate(data, partial)
        if data:
            try:
                self.trains.update(train_id, data)
            except sqlite3.IntegrityError:
                raise ConflictError("Train number already exists") from None
        self._invalidate(train_id)  # инвалидация кэша после изменения
        return self.get_train(train_id)

    def delete_train(self, train_id: int) -> None:
        if self.trains.get_by_id(train_id) is None:
            raise NotFoundError(f"Train {train_id} not found")
        if self.trains.has_tickets(train_id):
            raise ConflictError("Train has sold tickets and cannot be deleted")
        self.trains.delete(train_id)
        self._invalidate(train_id)

    # ---------- расписание (кэшируемые NoSQL-данные варианта 10) ----------
    def schedule(self, train_id: int) -> dict:
        key = f"train:{train_id}:schedule"
        cached = self.cache.get_json(key)
        if cached is not None:
            return {**cached, "source": "cache", "ttl": self.cache.ttl(key)}
        if self.trains.get_by_id(train_id) is None:
            raise NotFoundError(f"Train {train_id} not found")
        data = {"train_id": train_id, "stops": self.trains.schedule(train_id)}
        self.cache.set_json(key, data, SCHEDULE_TTL)
        return {**data, "source": "database", "ttl": SCHEDULE_TTL}

    def search(self, from_city: str, to_city: str) -> list[dict]:
        if not from_city or not to_city:
            raise ValidationError("Parameters 'from' and 'to' are required")
        self.cache.push_search(f"{from_city} -> {to_city}")
        return self.trains.search(from_city, to_city)

    def free_seats(self, train_id: int) -> list[dict]:
        if self.trains.get_by_id(train_id) is None:
            raise NotFoundError(f"Train {train_id} not found")
        result = []
        for wagon in self.trains.wagons(train_id):
            busy = self.trains.busy_seats(wagon["id"])
            free = [s for s in range(1, wagon["seats"] + 1) if s not in busy]
            result.append({"wagon": wagon["number"], "type": wagon["wagon_type"],
                           "free_count": len(free), "free_seats": free})
        return result

    # ---------- билеты: транзакция ----------
    def buy_ticket(self, data: dict) -> dict:
        """Покупка в одной транзакции: проверка поезда и места, пассажир (создать/найти), билет.
        Ошибка на любом шаге → ROLLBACK."""
        required = {"train_id", "wagon", "seat", "full_name", "passport"}
        if not isinstance(data, dict) or not required <= data.keys():
            raise ValidationError(f"Required fields: {sorted(required)}")
        db = self.trains.db
        try:
            db.execute("BEGIN")
            train = self.trains.get_by_id(int(data["train_id"]))
            if train is None:
                raise NotFoundError("Train not found")
            if train["status"] != "scheduled":
                raise ConflictError(f"Ticket sales closed: train is {train['status']}")
            wagon = next((w for w in self.trains.wagons(train["id"]) if w["number"] == int(data["wagon"])), None)
            if wagon is None:
                raise NotFoundError(f"Wagon {data['wagon']} not found")
            seat = int(data["seat"])
            if not 1 <= seat <= wagon["seats"]:
                raise ValidationError(f"Seat must be in 1..{wagon['seats']}")
            passenger = self.tickets.find_passenger(data["passport"])
            passenger_id = passenger["id"] if passenger else self.tickets.insert_passenger(
                data["full_name"], data["passport"], data.get("email"))
            price = round(train["base_price"] * COEFFICIENTS[wagon["wagon_type"]], 2)
            ticket_id = self.tickets.insert_ticket(wagon["id"], passenger_id, seat, price)
            db.execute("COMMIT")
        except sqlite3.IntegrityError:
            db.execute("ROLLBACK")
            raise ConflictError(f"Seat {data['seat']} is already taken") from None
        except (ValueError, TypeError):
            db.execute("ROLLBACK")
            raise ValidationError("train_id, wagon and seat must be integers") from None
        except Exception:
            db.execute("ROLLBACK")
            raise
        self._invalidate(train["id"])
        return self.tickets.get(ticket_id)

    def return_ticket(self, ticket_id: int) -> dict:
        ticket = self.tickets.get(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket {ticket_id} not found")
        if ticket["status"] == "returned":
            raise ConflictError("Ticket already returned")
        self.tickets.set_status(ticket_id, "returned")
        self.trains.db.commit()
        self._invalidate(ticket["train_id"])
        return {**self.tickets.get(ticket_id), "refund": round(ticket["price"] * 0.9, 2)}
