import fakeredis
import pytest

from app import create_app
from cache import RedisCache
from database import connect, init_db
from repository import TicketRepository, TrainRepository
from service import RailwayService


@pytest.fixture
def db():
    connection = connect(":memory:")
    init_db(connection)
    return connection


@pytest.fixture
def cache():
    return RedisCache(fakeredis.FakeRedis(decode_responses=True))


@pytest.fixture
def service(db, cache):
    return RailwayService(TrainRepository(db), TicketRepository(db), cache)


@pytest.fixture
def client(db, cache):
    return create_app(db, cache).test_client()
