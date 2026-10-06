"""Сущности предметной области — только данные и правила своего состояния (SRP)."""

from dataclasses import dataclass, field

from models.enums import TicketStatus


class DomainError(Exception):
    """Нарушение бизнес-правила."""


@dataclass
class Trip:
    id: int
    train_number: str
    route: str
    date: str
    base_price: float
    seats: int


@dataclass(frozen=True)
class Tariff:
    """Тариф: скидка и доля возврата. Льготный тариф — это другие ЧИСЛА,
    а не подкласс с «запрещённым» методом, поэтому LSP не нарушается."""
    name: str
    discount: float       # 0.5 = скидка 50%
    refund_share: float   # 0.0 … 1.0 — доля стоимости, возвращаемая при возврате


REGULAR = Tariff("обычный", 0.0, 0.9)
CONCESSION = Tariff("льготный", 0.5, 0.5)
STUDENT = Tariff("студенческий", 0.25, 0.75)


@dataclass
class Ticket:
    id: int
    trip_id: int
    passenger: str
    seat: int
    tariff: Tariff
    price: float
    status: TicketStatus = TicketStatus.BOOKED
    payment_method: str | None = field(default=None)

    def mark_paid(self, method_name: str) -> None:
        if self.status != TicketStatus.BOOKED:
            raise DomainError(f"Оплатить можно только забронированный билет (сейчас: {self.status.value})")
        self.status = TicketStatus.PAID
        self.payment_method = method_name

    def mark_refunded(self) -> float:
        if self.status == TicketStatus.REFUNDED:
            raise DomainError("Билет уже возвращён")
        amount = self.price * self.tariff.refund_share if self.status == TicketStatus.PAID else 0.0
        self.status = TicketStatus.REFUNDED
        return round(amount, 2)

    @property
    def is_active(self) -> bool:
        return self.status != TicketStatus.REFUNDED
