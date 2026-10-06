"""Тесты repository/service на SQLite в памяти (та же ORM-модель, что и для PostgreSQL)."""

from datetime import datetime

import pytest
from sqlalchemy.pool import StaticPool

from app.database import create_session_factory
from app.exceptions import BusinessRuleError, DuplicateError, NotFoundError, ValidationError
from app.models import Base, CarClass, DriverStatus, TripStatus
from app.repositories.repositories import TripRepository
from app.seed import seed
from app.services.services import TaxiService, calculate_cost


@pytest.fixture
def service():
    from sqlalchemy import create_engine, event
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    s = TaxiService(create_session_factory(engine))
    seed(s)
    return s


def test_crud_client(service):
    client = service.create_client("Тестов Тест", "+70000000000")
    assert service.get_client(client.id).full_name == "Тестов Тест"
    service.update_client(client.id, full_name="Тестов Т.")
    assert service.get_client(client.id).full_name == "Тестов Т."
    service.delete_client(client.id)
    with pytest.raises(NotFoundError):
        service.get_client(client.id)


def test_duplicate_phone(service):
    with pytest.raises(DuplicateError):
        service.create_client("Двойник", "+79001110001")


def test_search_and_pagination(service):
    assert [c.full_name for c in service.search_clients("ова")] == ["Кузнецова Мария", "Петрова Анна"]
    assert len(service.list_clients(page=2, page_size=3)) == 2


def test_driver_sorting_and_many_to_many(service):
    names = [d.full_name for d in service.drivers_sorted("experience")]
    assert names[0] == "Смирнов Олег"
    skoda_drivers = [d.full_name for d in service.drivers_with_cars() if any(c.plate == "К123КК777" for c in d.cars)]
    assert skoda_drivers == ["Смирнов Олег", "Волков Дмитрий"]


def test_create_trip_assigns_best_free_driver(service):
    trip = service.create_trip(2, "А", "Б", 10, 20, CarClass.ECONOMY)
    assert trip.status == TripStatus.ASSIGNED and trip.driver.full_name == "Новиков Артём"
    with pytest.raises(BusinessRuleError):           # оба водителя эконом-класса заняты
        service.create_trip(3, "А", "Б", 10, 20, CarClass.ECONOMY)


def test_transaction_rollback_when_no_driver(service):
    service.create_trip(2, "А", "Б", 10, 20, CarClass.ECONOMY)
    before = len(service.filter_trips())
    with pytest.raises(BusinessRuleError):
        service.create_trip(3, "А", "Б", 10, 20, CarClass.ECONOMY)
    assert len(service.filter_trips()) == before     # поездка не сохранилась


def test_full_trip_lifecycle_updates_driver(service):
    trip = service.create_trip(5, "Офис", "Дом", 20, 35, CarClass.BUSINESS)
    service.start_trip(trip.id)
    done = service.complete_trip(trip.id, actual_distance=22, driver_rating=4)
    assert done.status == TripStatus.COMPLETED and done.cost > 0
    driver = next(d for d in service.drivers_sorted("name") if d.full_name == "Смирнов Олег")
    assert driver.status == DriverStatus.FREE and driver.rating < 5


def test_invalid_operations(service):
    with pytest.raises(ValidationError):
        service.create_trip(1, "А", "Б", -5, 10, CarClass.ECONOMY)
    with pytest.raises(NotFoundError):
        service.create_trip(99, "А", "Б", 5, 10, CarClass.ECONOMY)
    with pytest.raises(BusinessRuleError):
        service.complete_trip(1)                       # уже завершена
    with pytest.raises(BusinessRuleError):
        service.delete_client(1)                       # есть история поездок


def test_filter_multiple_conditions_and_sort(service):
    trips = service.filter_trips(status=TripStatus.COMPLETED, min_cost=600, sort="cost", descending=False)
    costs = [t.cost for t in trips]
    assert costs == sorted(costs) and all(c >= 600 for c in costs)


@pytest.mark.parametrize("hour, expected", [(12, 99 + 14 * 10 + 6 * 20), (23, (99 + 140 + 120) * 1.25)])
def test_calculate_cost_day_and_night(hour, expected):
    assert calculate_cost(CarClass.ECONOMY, 10, 20, datetime(2026, 10, 1, hour)) == round(expected, 2)


def test_statistics_aggregates(service):
    stats = service.statistics()
    assert stats["count"] == 4 and stats["min_cost"] <= stats["avg_cost"] <= stats["max_cost"]
