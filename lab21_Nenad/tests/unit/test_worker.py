"""Outbox relay и идемпотентный обработчик событий."""

import pytest

from src.app.database import make_engine, make_session_factory
from src.app.events import InMemoryBroker, create_broker, retrying
from src.app.models import Base, Notification, OutboxEvent, User
from src.app.worker import handle_event, relay_outbox


@pytest.fixture
def db():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = make_session_factory(engine)()
    session.add(User(email="p@t.ru", password_hash="x$y", full_name="P", phone="+79000000000"))
    for number in (1, 2):
        session.add(OutboxEvent(event_id=f"e{number}", event_type="order.assigned",
                                payload={"order_id": number, "passenger_id": 1, "driver_id": 1, "status": "assigned",
                                         "price": 239.0, "route": "A → B", "driver_name": "Иван", "car": "Kia"}))
    session.commit()
    yield session
    session.close()


class FlakyBroker(InMemoryBroker):
    def __init__(self, failures):
        super().__init__()
        self.failures = failures

    def publish(self, event):
        if self.failures > 0:
            self.failures -= 1
            raise ConnectionError("broker down")
        super().publish(event)


def test_relay_publishes_and_marks(db):
    broker = InMemoryBroker()
    assert relay_outbox(db, broker) == 2
    assert [m["event_id"] for m in broker.messages] == ["e1", "e2"]
    assert relay_outbox(db, broker) == 0                           # повторно не отправляется


def test_relay_retries_transient_failure(db):
    broker = FlakyBroker(failures=2)
    assert relay_outbox(db, broker, attempts=3, delay=0) == 2


def test_relay_keeps_events_when_broker_down(db):
    broker = FlakyBroker(failures=100)
    assert relay_outbox(db, broker, attempts=2, delay=0) == 0
    assert db.query(OutboxEvent).filter_by(published=False).count() == 2   # ничего не потеряно
    broker.failures = 0
    assert relay_outbox(db, broker) == 2


def test_handler_is_idempotent(db):
    broker = InMemoryBroker()
    relay_outbox(db, broker)
    event = broker.messages[0]
    assert handle_event(db, event) is True
    assert handle_event(db, event) is False                        # повторная доставка
    notification = db.query(Notification).one()
    assert "Иван" in notification.text and "239.0" in notification.text


def test_consume_and_factory():
    broker = InMemoryBroker()
    broker.publish({"x": 1})
    received = []
    broker.consume("g", received.append, lambda: False)
    assert received == [{"x": 1}] and broker.ping()
    assert type(create_broker("redis://localhost:1")).__name__ == "RedisStreamBroker"
    assert type(create_broker("amqp://guest:guest@localhost:1/")).__name__ == "RabbitBroker"
    assert create_broker("redis://localhost:1").ping() is False
    with pytest.raises(ValueError):
        retrying(lambda: (_ for _ in ()).throw(ValueError("x")), attempts=2, delay=0)
