"""Отказоустойчивость: падение Redis, брокера и базы данных."""

from fastapi.testclient import TestClient

from src.app.cache import Cache
from src.app.config import Settings
from src.app.main import create_app
from tests.conftest import ORDER, register


class Broken:
    def __getattr__(self, name):
        raise ConnectionError("down")


class DownBroker:
    def publish(self, event):
        raise ConnectionError("broker down")

    def ping(self):
        return False


def test_api_works_without_redis_and_broker(settings):
    app = create_app(settings, Cache(Broken()), DownBroker())
    with TestClient(app) as client:
        health = client.get("/health").json()
        assert health == {"status": "degraded", "database": "ok", "redis": "unavailable", "broker": "unavailable"}
        headers = register(client)
        response = client.post("/orders", headers=headers, json=ORDER)
        assert response.status_code == 201                         # заказ создаётся, событие ждёт в outbox
        assert client.get("/drivers/1", headers=headers).headers["X-Cache"] == "MISS"


def test_database_down_returns_503():
    app = create_app(Settings(database_url="postgresql+psycopg://x:y@127.0.0.1:1/none", log_level="CRITICAL"),
                     Cache(), DownBroker(), seed=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/health").status_code == 503
        response = client.post("/auth/login", json={"email": "a@b.ru", "password": "x"})
        assert response.status_code == 503 and response.json()["error"] == "DATABASE_UNAVAILABLE"
