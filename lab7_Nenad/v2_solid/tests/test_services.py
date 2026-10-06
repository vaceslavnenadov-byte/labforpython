"""Тесты бизнес-логики без input()/print(): зависимости подменяются тестовыми."""

import pytest

from container import Container
from infrastructure.notifier import EmailNotifier
from interfaces.services import PaymentMethod
from models.entities import CONCESSION, REGULAR, DomainError, Trip
from models.enums import TicketStatus
from payments.methods import BonusPayment, CardPayment, CashPayment
from repositories.json_repository import JsonTicketRepository
from repositories.memory_repository import InMemoryTicketRepository, InMemoryTripRepository
from services.booking_service import BookingService, NotFoundError
from services.report_service import ReportService
from services.search_service import SearchService


class FakeNotifier:
    def __init__(self):
        self.messages = []

    def send(self, recipient, message):
        self.messages.append((recipient, message))


@pytest.fixture
def trips():
    repo = InMemoryTripRepository()
    repo.add(Trip(1, "001А", "Москва - Санкт-Петербург", "2026-10-10", 3000, 5))
    repo.add(Trip(2, "104В", "Москва - Казань", "2026-10-11", 2000, 3))
    return repo


@pytest.fixture
def notifier():
    return FakeNotifier()


@pytest.fixture
def booking(trips, notifier):
    return BookingService(trips, InMemoryTicketRepository(), notifier)


def test_book_ticket_creates_ticket_and_notifies(booking, notifier):
    ticket = booking.book(1, "Иванов", 2)
    assert ticket.price == 3000
    assert ticket.status == TicketStatus.BOOKED
    assert notifier.messages[0][0] == "Иванов"


def test_cannot_book_taken_seat(booking):
    booking.book(1, "Иванов", 2)
    with pytest.raises(DomainError, match="занято"):
        booking.book(1, "Петров", 2)


def test_concession_tariff_discount_and_partial_refund(booking):
    ticket = booking.book(2, "Сидорова", 1, CONCESSION)
    booking.buy(ticket.id, CashPayment())
    assert ticket.price == 1000
    assert booking.refund(ticket.id) == 500  # льготный билет возвращается, но на 50% (LSP соблюдён)


def test_card_payment_adds_commission(booking):
    ticket = booking.book(1, "Иванов", 1)
    assert booking.buy(ticket.id, CardPayment()) == 3045.0
    assert ticket.status == TicketStatus.PAID


def test_new_payment_method_without_changing_service(booking):
    class CryptoPayment(PaymentMethod):  # новая реализация «на лету» (OCP)
        name = "криптовалюта"

        def total(self, amount):
            return amount

        def pay(self, amount):
            return "TX"

    ticket = booking.book(1, "Иванов", 3)
    assert booking.buy(ticket.id, CryptoPayment()) == 3000
    assert ticket.payment_method == "криптовалюта"


def test_bonus_payment_insufficient_balance(booking):
    ticket = booking.book(1, "Иванов", 4)
    with pytest.raises(ValueError):
        booking.buy(ticket.id, BonusPayment(100))
    assert ticket.status == TicketStatus.BOOKED


def test_refund_frees_seat(booking):
    ticket = booking.book(2, "Иванов", 1)
    booking.refund(ticket.id)
    assert 1 in booking.free_seats(2)
    with pytest.raises(DomainError):
        booking.refund(ticket.id)


def test_unknown_trip_and_ticket(booking):
    with pytest.raises(NotFoundError):
        booking.book(99, "Иванов", 1)
    with pytest.raises(NotFoundError):
        booking.refund(99)


def test_search_filters_by_city_and_price(trips):
    service = SearchService(trips)
    assert [t.id for t in service.search("казань")] == [2]
    assert [t.id for t in service.search("москва", max_price=2500)] == [2]
    assert service.search("владивосток") == []


def test_report_counts_paid_tickets(booking, trips):
    t = booking.book(1, "А", 1)
    booking.buy(t.id, CashPayment())
    booking.book(1, "Б", 2)  # не оплачен — в отчёт не попадает
    report = ReportService(trips, booking.tickets).sales_report()
    assert report[0]["sold"] == 1 and report[0]["revenue"] == 3000


def test_json_repository_is_substitutable(trips, tmp_path):
    """LSP: сервис одинаково работает с памятью и файлом; данные переживают перезапуск."""
    path = tmp_path / "tickets.json"
    service = BookingService(trips, JsonTicketRepository(path), EmailNotifier())
    ticket = service.book(1, "Иванов", 5, REGULAR)
    service.buy(ticket.id, CashPayment())
    restored = JsonTicketRepository(path).get(ticket.id)
    assert restored.status == TicketStatus.PAID and restored.passenger == "Иванов"


def test_container_resolves_singletons():
    container = Container()
    container.register(InMemoryTicketRepository, InMemoryTicketRepository)
    assert container.resolve(InMemoryTicketRepository) is container.resolve(InMemoryTicketRepository)
    with pytest.raises(KeyError):
        container.resolve(SearchService)
