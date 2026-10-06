from fastapi.testclient import TestClient

from common.events import InMemoryBus
from common.resilience import ServiceClient
from conftest import down_transport, transport_to
from gateway.main import create_app
from passenger_service.main import create_app as passenger_app


def make_gateway(passengers_transport):
    clients = {"passengers": ServiceClient("passenger-service", "http://p", transport=passengers_transport,
                                           sleep=lambda s: None),
               "drivers": ServiceClient("driver-service", "http://d", transport=down_transport(), attempts=1)}
    return TestClient(create_app(clients))


def test_routing_through_gateway():
    passengers = TestClient(passenger_app("sqlite://", InMemoryBus()))
    gateway = make_gateway(transport_to(passengers))
    created = gateway.post("/api/passengers", json={"full_name": "Иван Иванов", "phone": "+79001112233"})
    assert created.status_code == 201
    assert gateway.get("/api/passengers/1").json()["phone"] == "+79001112233"
    assert "X-Request-ID" in created.headers


def test_unknown_resource_and_unavailable_service():
    gateway = make_gateway(down_transport())
    assert gateway.get("/api/planes").status_code == 404
    assert gateway.get("/api/drivers").status_code == 503


def test_status_shows_each_service():
    passengers = TestClient(passenger_app("sqlite://", InMemoryBus()))
    status = make_gateway(transport_to(passengers)).get("/status").json()
    assert status["passenger-service"] == "✓ healthy" and status["driver-service"].startswith("✗")


def test_gateway_passes_through_5xx_without_opening_breaker():
    import httpx
    client = ServiceClient("order-service", "http://o", fail_on_5xx=False,
                           transport=httpx.MockTransport(lambda r: httpx.Response(503, json={"detail": "dependency down"})))
    gateway = TestClient(create_app({"orders": client}))
    for _ in range(5):
        assert gateway.post("/api/orders", json={}).status_code == 503
    assert client.breaker.state.value == "CLOSED"
