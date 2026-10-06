from fastapi.testclient import TestClient

from common.events import InMemoryBus, make_event
from notification_service.main import create_app

PAYLOAD = {"order_id": 7, "passenger_id": 3, "driver_id": 1, "status": "assigned", "cost": 589.0, "route": "А → Б"}


def test_event_creates_notification():
    bus = InMemoryBus()
    client = TestClient(create_app("sqlite://", bus))
    bus.publish(make_event("OrderCreated", PAYLOAD, "order-service"))
    notes = client.get("/notifications", params={"passenger_id": 3}).json()
    assert len(notes) == 1 and "589.0" in notes[0]["text"]


def test_duplicate_event_is_ignored():
    bus = InMemoryBus()
    client = TestClient(create_app("sqlite://", bus))
    event = make_event("OrderStatusChanged", {**PAYLOAD, "status": "completed"}, "order-service")
    bus.publish(event)
    bus.publish(event)                                    # повторная доставка (at-least-once)
    assert len(client.get("/notifications").json()) == 1


def test_irrelevant_status_skipped():
    bus = InMemoryBus()
    client = TestClient(create_app("sqlite://", bus))
    bus.publish(make_event("OrderStatusChanged", {**PAYLOAD, "status": "assigned"}, "order-service"))
    assert client.get("/notifications").json() == []
