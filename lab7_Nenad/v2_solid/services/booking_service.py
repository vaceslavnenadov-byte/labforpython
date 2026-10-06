from interfaces.repository import TicketRepository, TripReader
from interfaces.services import Notifier, PaymentMethod
from models.entities import DomainError, Tariff, Ticket, REGULAR


class NotFoundError(DomainError):
    pass


class BookingService:
    """Бронирование, покупка и возврат. Все зависимости передаются извне (DIP)."""

    def __init__(self, trips: TripReader, tickets: TicketRepository, notifier: Notifier) -> None:
        self.trips = trips
        self.tickets = tickets
        self.notifier = notifier

    def _get_ticket(self, ticket_id: int) -> Ticket:
        ticket = self.tickets.get(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Билет №{ticket_id} не найден")
        return ticket

    def free_seats(self, trip_id: int) -> list[int]:
        trip = self.trips.get(trip_id)
        if trip is None:
            raise NotFoundError(f"Рейс №{trip_id} не найден")
        busy = {t.seat for t in self.tickets.find_by_trip(trip_id) if t.is_active}
        return [s for s in range(1, trip.seats + 1) if s not in busy]

    def book(self, trip_id: int, passenger: str, seat: int, tariff: Tariff = REGULAR) -> Ticket:
        if not passenger.strip():
            raise DomainError("Не указан пассажир")
        trip = self.trips.get(trip_id)
        if trip is None:
            raise NotFoundError(f"Рейс №{trip_id} не найден")
        if not 1 <= seat <= trip.seats:
            raise DomainError(f"Места пронумерованы от 1 до {trip.seats}")
        if seat not in self.free_seats(trip_id):
            raise DomainError(f"Место {seat} уже занято")
        price = round(trip.base_price * (1 - tariff.discount), 2)
        ticket = Ticket(self.tickets.next_id(), trip_id, passenger.strip(), seat, tariff, price)
        self.tickets.add(ticket)
        self.notifier.send(passenger, f"Билет №{ticket.id} забронирован: {trip.route}, место {seat}")
        return ticket

    def buy(self, ticket_id: int, payment: PaymentMethod) -> float:
        """Method Injection: способ оплаты передаётся в момент вызова."""
        ticket = self._get_ticket(ticket_id)
        amount = payment.total(ticket.price)
        transaction_id = payment.pay(amount)
        ticket.mark_paid(payment.name)
        self.tickets.update(ticket)
        self.notifier.send(ticket.passenger,
                           f"Билет №{ticket.id} оплачен ({payment.name}, {amount:.2f} руб., {transaction_id})")
        return amount

    def refund(self, ticket_id: int) -> float:
        ticket = self._get_ticket(ticket_id)
        amount = ticket.mark_refunded()
        self.tickets.update(ticket)
        self.notifier.send(ticket.passenger, f"Билет №{ticket.id} возвращён, к выплате {amount:.2f} руб.")
        return amount
