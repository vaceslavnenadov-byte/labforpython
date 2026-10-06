import pytest
from fastapi.testclient import TestClient

from common.events import InMemoryBus
from common.resilience import BreakerState, CircuitBreaker, ServiceClient
from conftest import down_transport, transport_to
from driver_service.main import create_app as driver_app
from order_service.main import calculate_cost, create_app
from passenger_service.main import create_app as passenger_app

ORDER = {"passenger_id": 1, "pickup": "Тверская, 1", "destination": "Шереметьево", "distance_km": 35, "car_class": "economy"}


@pytest.fixture
def system():
    """Три сервиса в памяти: Order → (HTTP) Passenger и Driver; общий брокер событий."""
    bus = InMemoryBus()
    passengers = TestClient(passenger_app("sqlite://", bus))
    drivers = TestClient(driver_app("sqlite://", bus))
    passengers.post("/passengers", json={"full_name": "Иван Иванов", "phone": "+79001112233"})
    drivers.post("/drivers", json={"full_name": "Олег Смирнов", "phone": "+79002220001", "car": "Kia Rio",
                                   "car_class": "economy"})
    orders = TestClient(create_app(
        "sqlite://", bus,
        passengers=ServiceClient("passenger-service", "http://p", transport=transport_to(passengers), sleep=lambda s: None),
        drivers=ServiceClient("driver-service", "http://d", transport=transport_to(drivers), sleep=lambda s: None)))
    return {"orders": orders, "passengers": passengers, "drivers": drivers, "bus": bus}


def test_cost_calculation():
    assert calculate_cost("economy", 10) == 239 and calculate_cost("business", 10) == 619


def test_create_order_calls_other_services_and_publishes_event(system):
    response = system["orders"].post("/orders", json=ORDER)
    assert response.status_code == 201 and response.json()["driver_id"] == 1
    assert system["drivers"].get("/drivers/1").json()["status"] == "busy"        # синхронный вызов Driver Service
    assert system["bus"].published[-1]["type"] == "OrderCreated"


def test_unknown_passenger_400(system):
    assert system["orders"].post("/orders", json={**ORDER, "passenger_id": 99}).status_code == 400


def test_no_free_driver_409(system):
    system["orders"].post("/orders", json=ORDER)
    assert system["orders"].post("/orders", json=ORDER).status_code == 409


def test_status_lifecycle_and_async_driver_release(system):
    order_id = system["orders"].post("/orders", json=ORDER).json()["id"]
    assert system["orders"].patch(f"/orders/{order_id}/status", json={"status": "completed"}).status_code == 409
    system["orders"].patch(f"/orders/{order_id}/status", json={"status": "in_progress"})
    system["orders"].patch(f"/orders/{order_id}/status", json={"status": "completed"})
    # событие OrderStatusChanged освободило водителя и увеличило счётчик поездок пассажира
    assert system["drivers"].get("/drivers/1").json()["status"] == "free"
    assert system["passengers"].get("/passengers/1").json()["trips_count"] == 1


def test_update_and_delete_rules(system):
    order_id = system["orders"].post("/orders", json=ORDER).json()["id"]
    changed = system["orders"].put(f"/orders/{order_id}", json={"pickup": "Арбат", "destination": "Внуково", "distance_km": 30})
    assert changed.json()["cost"] == calculate_cost("economy", 30)
    assert system["orders"].delete(f"/orders/{order_id}").status_code == 409
    system["orders"].patch(f"/orders/{order_id}/status", json={"status": "cancelled"})
    assert system["orders"].delete(f"/orders/{order_id}").status_code == 204


def test_passenger_service_down_gives_503_and_opens_circuit():
    breaker = CircuitBreaker("passenger-service", failure_threshold=2, recovery_timeout=60)
    calls = []
    transport = down_transport()
    passengers = ServiceClient("passenger-service", "http://p", attempts=3, breaker=breaker,
                               transport=transport, sleep=calls.append)
    orders = TestClient(create_app("sqlite://", InMemoryBus(), passengers=passengers,
                                   drivers=ServiceClient("driver-service", "http://d", transport=down_transport())))
    assert orders.post("/orders", json=ORDER).status_code == 503
    assert calls == [0.2, 0.4]                                   # Retry: 3 попытки с паузами
    orders.post("/orders", json=ORDER)
    assert breaker.state == BreakerState.OPEN
    response = orders.post("/orders", json=ORDER)                # дальше запросы не идут в упавший сервис
    assert response.status_code == 503 and "OPEN" in response.json()["detail"]
    assert orders.get("/circuit").json()["passenger-service"] == "OPEN"
