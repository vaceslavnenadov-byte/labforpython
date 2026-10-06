from dataclasses import asdict, dataclass
from enum import Enum


class TrainStatus(str, Enum):
    SCHEDULED = "scheduled"
    BOARDING = "boarding"
    DEPARTED = "departed"
    CANCELLED = "cancelled"


@dataclass
class Train:
    id: int
    number: str
    departure_station: str
    arrival_station: str
    departure_time: str      # ISO-формат: 2026-10-10T23:55
    arrival_time: str
    wagons: int
    seats_per_wagon: int
    booked_seats: int
    price: float
    status: TrainStatus = TrainStatus.SCHEDULED

    @property
    def total_seats(self) -> int:
        return self.wagons * self.seats_per_wagon

    @property
    def free_seats(self) -> int:
        return self.total_seats - self.booked_seats

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        data["route"] = f"{self.departure_station} - {self.arrival_station}"
        data["total_seats"] = self.total_seats
        data["free_seats"] = self.free_seats
        return data
