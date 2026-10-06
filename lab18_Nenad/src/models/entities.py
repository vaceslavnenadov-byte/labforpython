from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TicketStatus(str, Enum):
    SOLD = "sold"
    RETURNED = "returned"


@dataclass
class Route:
    """Рейс поезда по маршруту на конкретную дату."""
    id: int | None
    train_number: str
    from_city: str
    to_city: str
    departure: datetime
    seats: int
    price: float


@dataclass
class Ticket:
    id: int | None
    route_id: int
    passenger: str
    seat: int
    price: float
    status: TicketStatus = TicketStatus.SOLD
    sold_at: datetime | None = None
