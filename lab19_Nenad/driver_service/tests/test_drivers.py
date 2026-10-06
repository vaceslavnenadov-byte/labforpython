from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from common.events import InMemoryBus, make_event
from driver_service.main import create_app

DRIVER = {"full_name": "Олег Смирнов", "phone": "+79002220001", "car": "Kia Rio", "car_class": "economy"}


def make_client(bus=None):
    return TestClient(create_app("sqlite://", bus or InMemoryBus()))


def add(client, **changes):
    return client.post("/drivers", json={**DRIVER, **changes}).json()


def test_create_and_filter():
    client = make_client()
    add(client)
    add(client, phone="+79002220002", car_class="business", car="Mercedes")
    assert [d["car_class"] for d in client.get("/drivers", params={"car_class": "business"}).json()] == ["business"]


def test_assign_marks_busy_and_no_free_409():
    client = make_client()
    driver = add(client)
    assigned = client.post("/drivers/assign", json={"car_class": "economy"})
    assert assigned.json()["id"] == driver["id"] and assigned.json()["status"] == "busy"
    assert client.post("/drivers/assign", json={"car_class": "economy"}).status_code == 409


def test_concurrent_assign_gives_driver_once():
    client = make_client()
    add(client)
    with ThreadPoolExecutor(4) as pool:
        codes = list(pool.map(lambda _: client.post("/drivers/assign", json={"car_class": "economy"}).status_code, range(4)))
    assert sorted(codes) == [200, 409, 409, 409]


def test_release_is_idempotent():
    client = make_client()
    driver = add(client)
    client.post("/drivers/assign", json={"car_class": "economy"})
    assert client.post(f"/drivers/{driver['id']}/release").json()["status"] == "free"
    assert client.post(f"/drivers/{driver['id']}/release").json()["status"] == "free"


def test_cannot_delete_busy_driver():
    client = make_client()
    driver = add(client)
    client.post("/drivers/assign", json={"car_class": "economy"})
    assert client.delete(f"/drivers/{driver['id']}").status_code == 409


def test_order_events_free_driver():
    bus = InMemoryBus()
    client = make_client(bus)
    driver = add(client)
    client.post("/drivers/assign", json={"car_class": "economy"})
    bus.publish(make_event("OrderStatusChanged", {"driver_id": driver["id"], "status": "completed"}, "test"))
    result = client.get(f"/drivers/{driver['id']}").json()
    assert result["status"] == "free" and result["trips_count"] == 1


def test_status_and_404():
    client = make_client()
    driver = add(client)
    assert client.patch(f"/drivers/{driver['id']}/status", json={"status": "offline"}).json()["status"] == "offline"
    assert client.get("/drivers/999").status_code == 404
