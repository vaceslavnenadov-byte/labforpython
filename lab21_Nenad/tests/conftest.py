import os

import fakeredis
import pytest
from fastapi.testclient import TestClient

from src.app.cache import Cache
from src.app.config import Settings
from src.app.events import InMemoryBroker
from src.app.main import create_app

ADMIN = {"email": "admin@taxi.ru", "password": "admin-pass-123"}


@pytest.fixture
def settings():
    return Settings(database_url=os.getenv("TEST_DATABASE_URL", "sqlite://"),
                    jwt_secret="test-secret-key-32-bytes-long!!",
                    admin_email=ADMIN["email"], admin_password=ADMIN["password"], log_level="WARNING")


@pytest.fixture
def cache():
    return Cache(fakeredis.FakeRedis(decode_responses=True), ttl=60)


@pytest.fixture
def broker():
    return InMemoryBroker()


@pytest.fixture
def app(settings, cache, broker):
    from src.app.models import Base
    application = create_app(settings, cache, broker)
    Base.metadata.drop_all(application.state.engine)
    return application


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def register(client, email="pass@taxi.ru", phone="+79001112233", password="secret-123"):
    response = client.post("/auth/register", json={"email": email, "password": password,
                                                   "full_name": "Пассажир Тестов", "phone": phone})
    assert response.status_code == 201, response.text
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_headers(client):
    return register(client)


@pytest.fixture
def admin_headers(client):
    token = client.post("/auth/login", json=ADMIN).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


ORDER = {"pickup": "ул. Ленина, 1", "destination": "Аэропорт Шереметьево", "distance_km": 10, "car_class": "economy"}
