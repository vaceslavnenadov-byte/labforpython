"""Интеграционные тесты против настоящих PostgreSQL и Redis (в CI — сервисы GitHub Actions)."""

import os

import pytest
from fastapi.testclient import TestClient

from src.cache import create_cache
from src.config import Settings
from src.main import create_app

pytestmark = pytest.mark.integration
DATABASE_URL = os.getenv("TEST_DATABASE_URL")
REDIS_URL = os.getenv("TEST_REDIS_URL")


@pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL не задан")
def test_ride_persists_in_postgres():
    settings = Settings(DATABASE_URL, REDIS_URL, 30, "WARNING", "ci")
    with TestClient(create_app(settings, create_cache(REDIS_URL, 30))) as client:
        driver = client.post("/drivers", json={"full_name": "Тест Тестов", "car_plate": f"CI{os.getpid()}",
                                               "car_class": "business"}).json()
        ride = client.post("/rides", json={"passenger": "CI", "driver_id": driver["id"], "pickup": "А1",
                                           "destination": "Б1", "distance_km": 10}).json()
    # новое приложение = «перезапуск контейнера»: данные остались в БД
    with TestClient(create_app(settings, create_cache(None, 30))) as client:
        assert client.get(f"/rides/{ride['id']}").json()["cost"] == 619
        assert client.get("/health").json()["database"] == "up"
