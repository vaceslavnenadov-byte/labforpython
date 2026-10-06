"""Модели: поезд, вагон, билет (dataclass + Enum)."""

from dataclasses import dataclass, field
from enum import Enum

from decorators import require_status
from exceptions import ValidationError


class WagonType(Enum):
    SEATED = ("сидячий", 60, 1.0)
    COUPE = ("купе", 36, 1.8)
    SV = ("СВ", 18, 3.0)

    def __init__(self, title: str, seats: int, coefficient: float):
        self.title = title
        self.seats = seats
        self.coefficient = coefficient


class TicketStatus(Enum):
    BOOKED = "забронирован"
    PAID = "оплачен"
    USED = "использован"
    RETURNED = "возвращён"


ACTIVE_STATUSES = (TicketStatus.BOOKED, TicketStatus.PAID, TicketStatus.USED)


@dataclass
class Entity:
    id: int


@dataclass
class Wagon(Entity):
    number: int
    wagon_type: WagonType

    @property
    def seats(self) -> int:
        return self.wagon_type.seats

    def get_report_data(self) -> str:
        return f"Вагон №{self.number} ({self.wagon_type.title}, {self.seats} мест)"


@dataclass
class Train(Entity):
    number: str
    route: str
    departure: str
    base_price: float
    wagons: list[Wagon] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.base_price <= 0:
            raise ValidationError("Базовая цена должна быть положительной")
        if not self.route.strip():
            raise ValidationError("Маршрут не может быть пустым")

    def capacity(self) -> int:
        return sum(wagon.seats for wagon in self.wagons)

    def find_wagon(self, number: int) -> Wagon | None:
        return next((w for w in self.wagons if w.number == number), None)

    def seat_price(self, wagon: Wagon) -> float:
        return round(self.base_price * wagon.wagon_type.coefficient, 2)

    def get_report_data(self) -> str:
        return (f"Поезд {self.number} «{self.route}», отправление {self.departure}, "
                f"вагонов: {len(self.wagons)}, мест: {self.capacity()}")


@dataclass
class Ticket(Entity):
    train_id: int
    wagon_number: int
    seat: int
    passenger: str
    price: float
    status: TicketStatus = TicketStatus.BOOKED

    @require_status(TicketStatus.BOOKED)
    def pay(self) -> None:
        self.status = TicketStatus.PAID

    @require_status(TicketStatus.PAID)
    def use(self) -> None:
        self.status = TicketStatus.USED

    @require_status(TicketStatus.BOOKED, TicketStatus.PAID)
    def refund(self) -> float:
        """Возврат: за оплаченный билет возвращается 90% стоимости."""
        refund_sum = self.price * 0.9 if self.status == TicketStatus.PAID else 0.0
        self.status = TicketStatus.RETURNED
        return round(refund_sum, 2)

    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES

    def get_report_data(self) -> str:
        return (f"Билет #{self.id}: {self.passenger}, поезд id={self.train_id}, "
                f"вагон {self.wagon_number}, место {self.seat}, {self.price:.2f} руб., "
                f"{self.status.value}")
