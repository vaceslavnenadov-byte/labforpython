from dataclasses import asdict, dataclass
from enum import Enum


class RoomType(str, Enum):
    SINGLE = "single"
    DOUBLE = "double"
    SUITE = "suite"


@dataclass
class Room:
    id: int
    number: str
    room_type: RoomType
    floor: int
    price: float
    capacity: int
    is_free: bool = True
    guest: str | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["room_type"] = self.room_type.value
        return data
