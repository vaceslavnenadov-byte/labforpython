from fastapi.testclient import TestClient

from common.events import InMemoryBus, make_event
from passenger_service.main import create_app

PASSENGER = {"full_name": "Иван Иванов", "phone": "+79001112233"}


def make_client(bus=None):
    return TestClient(create_app("sqlite://", bus or InMemoryBus()))


def test_create_and_get():
    client = make_client()
    created = client.post("/passengers", json=PASSENGER)
    assert created.status_code == 201
    assert client.get(f"/passengers/{created.json()['id']}").json()["full_name"] == "Иван Иванов"


def test_duplicate_phone_409():
    client = make_client()
    client.post("/passengers", json=PASSENGER)
    assert client.post("/passengers", json=PASSENGER).status_code == 409


def test_validation_400():
    assert make_client().post("/passengers", json={"full_name": "И", "phone": "abc"}).status_code == 422


def test_update_delete_404():
    client = make_client()
    pid = client.post("/passengers", json=PASSENGER).json()["id"]
    assert client.put(f"/passengers/{pid}", json={**PASSENGER, "full_name": "Пётр Петров"}).json()["full_name"] == "Пётр Петров"
    assert client.delete(f"/passengers/{pid}").status_code == 204
    assert client.get(f"/passengers/{pid}").status_code == 404


def test_list_and_health():
    client = make_client()
    client.post("/passengers", json=PASSENGER)
    assert len(client.get("/passengers").json()) == 1
    assert client.get("/health").json() == {"status": "healthy", "service": "passenger-service"}


def test_completed_order_event_increments_trips():
    bus = InMemoryBus()
    client = make_client(bus)
    pid = client.post("/passengers", json=PASSENGER).json()["id"]
    bus.publish(make_event("OrderStatusChanged", {"passenger_id": pid, "status": "completed"}, "test"))
    bus.publish(make_event("OrderStatusChanged", {"passenger_id": pid, "status": "cancelled"}, "test"))
    assert client.get(f"/passengers/{pid}").json()["trips_count"] == 1


def test_data_persists_in_own_database(tmp_path):
    url = f"sqlite:///{tmp_path}/passengers.db"
    TestClient(create_app(url, InMemoryBus())).post("/passengers", json=PASSENGER)
    assert len(TestClient(create_app(url, InMemoryBus())).get("/passengers").json()) == 1
