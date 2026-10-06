"""Модели предметной области (dataclass)."""

from dataclasses import dataclass, field
from typing import ClassVar
from datetime import date

from models.enums import TicketStatus, WagonCategory


class DomainError(Exception):
    pass


@dataclass
class Train:
    number: str
    route: str
    departure: date
    base_price: float
    capacity: dict[WagonCategory, int] = field(default_factory=dict)


@dataclass
class Ticket:
    """Базовый билет. Конкретные классы задают коэффициент и услуги."""
    id: int
    train_number: str
    passenger: str
    seat: int
    price: float = 0.0
    tariff: str = ""
    status: TicketStatus = TicketStatus.SOLD

    category = WagonCategory.SEATED
    title = "билет"
    coefficient = 1.0
    services: ClassVar[tuple[str, ...]] = ()

    def describe(self) -> str:
        services = ", ".join(self.services) or "без услуг"
        return (f"#{self.id} {self.title:<8} поезд {self.train_number}, {self.passenger}, место {self.seat}, "
                f"{self.price:.2f} руб. [{self.tariff}] ({services}) — {self.status.value}")


@dataclass
class SeatedTicket(Ticket):
    category = WagonCategory.SEATED
    title = "Сидячий"
    coefficient = 1.0
    services = ()


@dataclass
class CoupeTicket(Ticket):
    category = WagonCategory.COUPE
    title = "Купе"
    coefficient = 1.8
    services = ("постельное бельё",)


@dataclass
class SvTicket(Ticket):
    category = WagonCategory.SV
    title = "СВ"
    coefficient = 3.0
    services = ("постельное бельё", "питание", "двухместное купе")
