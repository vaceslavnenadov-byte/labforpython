"""Бизнес-логика отеля. Ничего не знает о сокетах."""

from models import Room, RoomType
from exceptions import ConflictError, RoomNotFoundError, ValidationError
from repository import RoomRepository

EDITABLE_FIELDS = {"number", "room_type", "floor", "price", "capacity"}


class RoomService:
    def __init__(self, repository: RoomRepository) -> None:
        self.repository = repository

    # ---------- проверки ----------
    @staticmethod
    def _validate(data: dict) -> dict:
        clean = {}
        if "number" in data:
            number = str(data["number"]).strip()
            if not number:
                raise ValidationError("number must not be empty")
            clean["number"] = number
        if "room_type" in data:
            try:
                clean["room_type"] = RoomType(data["room_type"])
            except ValueError:
                raise ValidationError(f"room_type must be one of {[t.value for t in RoomType]}") from None
        for field, cast, minimum in (("floor", int, 1), ("capacity", int, 1), ("price", float, 0.01)):
            if field in data:
                try:
                    value = cast(data[field])
                except (TypeError, ValueError):
                    raise ValidationError(f"{field} must be a number") from None
                if value < minimum:
                    raise ValidationError(f"{field} must be >= {minimum}")
                clean[field] = value
        return clean

    def _ensure_unique_number(self, number: str, exclude_id: int | None = None) -> None:
        for room in self.repository.get_all():
            if room.number == number and room.id != exclude_id:
                raise ConflictError(f"Room number {number} already exists")

    # ---------- CRUD ----------
    def list_rooms(self) -> list[Room]:
        return sorted(self.repository.get_all(), key=lambda r: r.number)

    def get_room(self, room_id: int) -> Room:
        room = self.repository.get(room_id)
        if room is None:
            raise RoomNotFoundError(room_id)
        return room

    def create_room(self, data: dict) -> Room:
        missing = EDITABLE_FIELDS - data.keys()
        if missing:
            raise ValidationError(f"missing fields: {', '.join(sorted(missing))}")
        clean = self._validate(data)
        with self.repository.lock:
            self._ensure_unique_number(clean["number"])
            return self.repository.add(Room(id=0, **clean))

    def update_room(self, room_id: int, data: dict) -> Room:
        unknown = set(data) - EDITABLE_FIELDS
        if unknown:
            raise ValidationError(f"unknown fields: {', '.join(sorted(unknown))}")
        clean = self._validate(data)
        with self.repository.lock:
            room = self.get_room(room_id)
            if "number" in clean:
                self._ensure_unique_number(clean["number"], exclude_id=room_id)
            for key, value in clean.items():
                setattr(room, key, value)
            return self.repository.update(room)

    def delete_room(self, room_id: int) -> None:
        with self.repository.lock:
            room = self.get_room(room_id)
            if not room.is_free:
                raise ConflictError(f"Room {room.number} is occupied and cannot be deleted")
            self.repository.delete(room_id)

    # ---------- специализированные операции варианта 10 ----------
    def find_free_rooms(self, room_type: str | None = None, min_capacity: int = 1,
                        max_price: float | None = None) -> list[Room]:
        if room_type is not None:
            room_type = self._validate({"room_type": room_type})["room_type"]
        result = [
            r for r in self.repository.get_all()
            if r.is_free
            and (room_type is None or r.room_type == room_type)
            and r.capacity >= int(min_capacity)
            and (max_price is None or r.price <= float(max_price))
        ]
        return sorted(result, key=lambda r: r.price)

    def check_in(self, room_id: int, guest: str) -> Room:
        if not guest or not str(guest).strip():
            raise ValidationError("guest must not be empty")
        with self.repository.lock:  # исключает заселение двух гостей одновременно
            room = self.get_room(room_id)
            if not room.is_free:
                raise ConflictError(f"Room {room.number} is already occupied")
            room.is_free, room.guest = False, str(guest).strip()
            return self.repository.update(room)

    def check_out(self, room_id: int) -> Room:
        with self.repository.lock:
            room = self.get_room(room_id)
            if room.is_free:
                raise ConflictError(f"Room {room.number} is already free")
            room.is_free, room.guest = True, None
            return self.repository.update(room)

    def statistics(self) -> dict:
        rooms = self.repository.get_all()
        free = [r for r in rooms if r.is_free]
        return {
            "total": len(rooms),
            "free": len(free),
            "occupied": len(rooms) - len(free),
            "occupancy_percent": round((len(rooms) - len(free)) / len(rooms) * 100, 1) if rooms else 0,
            "average_price": round(sum(r.price for r in rooms) / len(rooms), 2) if rooms else 0,
        }


def seed(service: RoomService) -> None:
    demo = [
        ("101", "single", 1, 3200, 1), ("102", "single", 1, 3200, 1), ("103", "double", 1, 4800, 2),
        ("201", "double", 2, 5200, 2), ("202", "double", 2, 5200, 3), ("301", "suite", 3, 12000, 4),
    ]
    for number, room_type, floor, price, capacity in demo:
        service.create_room({"number": number, "room_type": room_type, "floor": floor,
                             "price": price, "capacity": capacity})
    service.check_in(3, "Иванов И.И.")
