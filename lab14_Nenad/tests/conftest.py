import os
import tempfile

# отдельная тестовая БД — задаётся ДО импорта приложения
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.gettempdir()}/railway_test_lab14.db"
os.environ.pop("REDIS_URL", None)

import fakeredis  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.cache import Cache, get_cache  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402

NEW_TRAIN = {
    "number": "777М", "route": "Москва - Тверь", "stations": ["Москва", "Клин", "Тверь"],
    "departure_time": "2026-10-20T08:00:00", "arrival_time": "2026-10-20T10:30:00",
    "wagons_count": 6, "price": 900,
}


@pytest.fixture
def cache():
    return Cache(fakeredis.FakeRedis(decode_responses=True), ttl=60)


@pytest.fixture
def client(cache):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    app.dependency_overrides[get_cache] = lambda: cache
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers(client):
    token = client.post("/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_headers(client):
    client.post("/auth/register", json={"username": "ivan", "password": "secret1"})
    token = client.post("/auth/login", json={"username": "ivan", "password": "secret1"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
