"""Интеграционные тесты: Service → Repository → SQLite (без Mock-объектов для хранилища)."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.exceptions import NoSeatsError
from src.repositories.sqlite_repository import RouteRepository, TicketRepository, connect
from src.services.ticket_service import TicketService

pytestmark = pytest.mark.integration
NOW = datetime(2026, 10, 1, 12, 0)


@pytest.fixture
def db(tmp_path):
    connection = connect(str(tmp_path / "test.db"))
    yield connection
    connection.close()


@pytest.fixture
def service(db):
    with patch("src.services.ticket_service.now", return_value=NOW):
        yield TicketService(RouteRepository(db), TicketRepository(db), Mock())


def test_full_cycle_sell_return_resell(service):
    route = service.create_route("001А", "Москва", "Санкт-Петербург", datetime(2026, 10, 10, 23, 55), 2, 3200)
    first = service.sell_ticket(route.id, "Иванов")
    second = service.sell_ticket(route.id, "Петров")
    assert (first.seat, second.seat) == (1, 2)
    with pytest.raises(NoSeatsError):
        service.sell_ticket(route.id, "Сидоров")
    assert service.return_ticket(first.id) == 2880.0
    assert service.sell_ticket(route.id, "Сидоров").seat == 1          # место освободилось
    assert [t.status.value for t in service.passenger_tickets("Иванов")] == ["returned"]


def test_search_by_city_and_date(service):
    service.create_route("001А", "Москва", "Санкт-Петербург", datetime(2026, 10, 10, 23, 55), 10, 3200)
    service.create_route("752А", "Москва", "Санкт-Петербург", datetime(2026, 10, 11, 6, 50), 10, 4100)
    service.create_route("104В", "Москва", "Казань", datetime(2026, 10, 10, 21, 20), 10, 2400)
    assert [r.train_number for r in service.search("москва", "санкт-петербург")] == ["001А", "752А"]
    assert [r.train_number for r in service.search("Москва", "Санкт-Петербург", "2026-10-11")] == ["752А"]


def test_unique_index_protects_seat(db):
    """Даже в обход сервиса БД не даст продать одно место дважды."""
    import sqlite3
    from src.models.entities import Route, Ticket
    route = RouteRepository(db).add(Route(None, "001А", "А", "Б", datetime(2026, 12, 1), 5, 100))
    tickets = TicketRepository(db)
    tickets.add(Ticket(None, route.id, "Иванов", 1, 100))
    with pytest.raises(sqlite3.IntegrityError):
        tickets.add(Ticket(None, route.id, "Петров", 1, 100))
