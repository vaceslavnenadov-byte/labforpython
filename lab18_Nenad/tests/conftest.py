from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.models.entities import Route, Ticket, TicketStatus
from src.repositories.sqlite_repository import RouteRepository, TicketRepository
from src.services.ticket_service import TicketService

NOW = datetime(2026, 10, 1, 12, 0)
DEPARTURE = datetime(2026, 10, 5, 12, 0)


@pytest.fixture
def fixed_now():
    """Подменяем текущее время там, где оно используется — в модуле сервиса."""
    with patch("src.services.ticket_service.now", return_value=NOW) as mocked:
        yield mocked


@pytest.fixture
def route():
    return Route(1, "001А", "Москва", "Санкт-Петербург", DEPARTURE, seats=3, price=3000.0)


@pytest.fixture
def routes_repo(route):
    repo = Mock(spec=RouteRepository)
    repo.find_by_id.return_value = route
    repo.exists.return_value = False
    repo.add.side_effect = lambda r: Route(10, r.train_number, r.from_city, r.to_city, r.departure, r.seats, r.price)
    return repo


@pytest.fixture
def tickets_repo():
    repo = Mock(spec=TicketRepository)
    repo.taken_seats.return_value = set()
    repo.add.side_effect = lambda t: Ticket(100, t.route_id, t.passenger, t.seat, t.price, t.status, t.sold_at)
    return repo


@pytest.fixture
def notifier():
    return Mock()


@pytest.fixture
def service(routes_repo, tickets_repo, notifier, fixed_now):
    return TicketService(routes_repo, tickets_repo, notifier)


@pytest.fixture
def sold_ticket():
    return Ticket(100, 1, "Иванов", 2, 3000.0, TicketStatus.SOLD, NOW)
