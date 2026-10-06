import fakeredis
import mongomock
import pytest

from app.cache import RedisCache
from app.repository import MongoRepository
from app.seed import generate
from app.service import TrainService


@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def service(redis_client):
    repo = MongoRepository(mongomock.MongoClient().get_database("test"))
    repo.create_indexes()
    svc = TrainService(repo, RedisCache(redis_client, ttl=60))
    for doc in generate():
        svc.add_train(doc)
    return svc
