"""Бизнес-логика продажи ж/д билетов."""

from datetime import datetime, timedelta
from typing import Protocol

from src.exceptions import NoSeatsError, NotFoundError, OperationNotAllowedError, ValidationError
from src.models.entities import Route, Ticket, TicketStatus

MAX_SEATS = 1000


class Notifier(Protocol):
    def send(self, passenger: str, message: str) -> None: ...


def now() -> datetime:
    """Отдельная функция для текущего времени — её удобно подменять через patch в тестах."""
    return datetime.now()


def refund_share(hours_before_departure: float) -> float:
    """Доля возврата: за сутки и более — 90%, позже — 50%, после отправления — 0."""
    if hours_before_departure <= 0:
        return 0.0
    if hours_before_departure >= 24:
        return 0.9
    return 0.5


class TicketService:
    def __init__(self, routes, tickets, notifier: Notifier) -> None:
        self.routes = routes
        self.tickets = tickets
        self.notifier = notifier

    # ---------- маршруты ----------
    def create_route(self, train_number: str, from_city: str, to_city: str, departure: datetime,
                     seats: int, price: float) -> Route:
        if not train_number or not train_number.strip():
            raise ValidationError("Номер поезда обязателен")
        if not from_city.strip() or not to_city.strip():
            raise ValidationError("Города отправления и назначения обязательны")
        if from_city.strip().lower() == to_city.strip().lower():
            raise ValidationError("Города отправления и назначения должны различаться")
        if not 1 <= seats <= MAX_SEATS:
            raise ValidationError(f"Количество мест должно быть от 1 до {MAX_SEATS}")
        if price <= 0:
            raise ValidationError("Цена должна быть положительной")
        if departure <= now():
            raise ValidationError("Дата отправления должна быть в будущем")
        if self.routes.exists(train_number, departure):
            raise ValidationError("Такой рейс уже существует")
        return self.routes.add(Route(None, train_number.strip(), from_city.strip(), to_city.strip(),
                                     departure, seats, price))

    def get_route(self, route_id: int) -> Route:
        route = self.routes.find_by_id(route_id)
        if route is None:
            raise NotFoundError(f"Рейс {route_id} не найден")
        return route

    def search(self, from_city: str, to_city: str, day: str | None = None, only_available: bool = True) -> list[Route]:
        result = self.routes.search(from_city, to_city, day)
        current = now()
        result = [r for r in result if r.departure > current]
        if only_available:
            result = [r for r in result if self.free_seats(r.id)]
        return result

    # ---------- места ----------
    def free_seats(self, route_id: int) -> list[int]:
        route = self.get_route(route_id)
        taken = self.tickets.taken_seats(route_id)
        return [s for s in range(1, route.seats + 1) if s not in taken]

    def has_free_seats(self, route_id: int) -> bool:
        return bool(self.free_seats(route_id))

    # ---------- продажа и возврат ----------
    def sell_ticket(self, route_id: int, passenger: str, seat: int | None = None) -> Ticket:
        if not passenger or not passenger.strip():
            raise ValidationError("Не указан пассажир")
        route = self.get_route(route_id)
        if route.departure <= now():
            raise OperationNotAllowedError("Поезд уже отправился")
        free = self.free_seats(route_id)
        if not free:
            raise NoSeatsError("Свободных мест нет")
        if seat is None:
            seat = free[0]
        elif not 1 <= seat <= route.seats:
            raise ValidationError(f"Номер места должен быть от 1 до {route.seats}")
        elif seat not in free:
            raise NoSeatsError(f"Место {seat} занято")
        ticket = self.tickets.add(Ticket(None, route_id, passenger.strip(), seat, route.price, sold_at=now()))
        self.notifier.send(ticket.passenger, f"Билет №{ticket.id}: поезд {route.train_number}, место {seat}")
        return ticket

    def return_ticket(self, ticket_id: int) -> float:
        ticket = self.tickets.find_by_id(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Билет {ticket_id} не найден")
        if ticket.status == TicketStatus.RETURNED:
            raise OperationNotAllowedError("Билет уже возвращён")
        route = self.get_route(ticket.route_id)
        hours = (route.departure - now()) / timedelta(hours=1)
        share = refund_share(hours)
        if share == 0:
            raise OperationNotAllowedError("После отправления поезда билет вернуть нельзя")
        self.tickets.update_status(ticket_id, TicketStatus.RETURNED)
        amount = round(ticket.price * share, 2)
        self.notifier.send(ticket.passenger, f"Билет №{ticket_id} возвращён, к выплате {amount} руб.")
        return amount

    def passenger_tickets(self, passenger: str) -> list[Ticket]:
        return self.tickets.find_by_passenger(passenger)
