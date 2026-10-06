import fakeredis
import pytest
from fastapi.testclient import TestClient

from src.cache import Cache
from src.config import Settings
from src.main import create_app


@pytest.fixture
def cache():
    return Cache(fakeredis.FakeRedis(decode_responses=True), ttl=60)


@pytest.fixture
def client(tmp_path, cache):
    settings = Settings(database_url=f"sqlite:///{tmp_path}/test.db", redis_url=None, cache_ttl=60,
                        log_level="WARNING", app_env="test")
    with TestClient(create_app(settings, cache)) as test_client:
        yield test_client


@pytest.fixture
def driver(client):
    return client.post("/drivers", json={"full_name": "Олег Смирнов", "car_plate": "А001АА777",
                                         "car_class": "economy"}).json()
