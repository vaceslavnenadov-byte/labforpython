"""Unit-тесты бизнес-правил на уровне сервисов (SQLite в памяти, кэш без Redis)."""

import fakeredis
import pytest

from src.app.cache import Cache
from src.app.database import make_engine, make_session_factory
from src.app.exceptions import BusinessRuleException, EntityNotFoundException, ForbiddenException
from src.app.models import Base, CarClass, DriverStatus, OrderStatus, OutboxEvent, Role, User
from src.app.schemas import CarIn, DriverIn, DriverUpdate, OrderIn
from src.app.seed import seed_fleet
from src.app.services.services import FleetService, OrderService


@pytest.fixture
def db():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = make_session_factory(engine)()
    seed_fleet(session)
    yield session
    session.close()


@pytest.fixture
def passenger(db):
    user = User(email="p@t.ru", password_hash="x$y", full_name="P", phone="+79000000000")
    admin = User(email="a@t.ru", password_hash="x$y", full_name="A", phone="+79000000009", role=Role.ADMIN)
    db.add_all([user, admin])
    db.commit()
    return user


def admin(db):
    return db.query(User).filter_by(role=Role.ADMIN).one()


def order_in(car_class="economy"):
    return OrderIn(pickup="Тверская, 1", destination="Арбат, 5", distance_km=5, car_class=car_class)


def test_best_rated_free_driver_assigned(db, passenger):
    order = OrderService(db, Cache()).create(passenger, order_in())
    assert order.driver.full_name == "Иван Петров"                 # рейтинг 4.9 > 4.6
    assert order.driver.status == DriverStatus.BUSY
    assert order.price == 199.0                                   # 99+14*5=169 < минимума 199
    event = db.query(OutboxEvent).one()
    assert event.event_type == "order.assigned" and event.payload["order_id"] == order.id


def test_one_active_order_per_passenger(db, passenger):
    service = OrderService(db, Cache())
    service.create(passenger, order_in())
    with pytest.raises(BusinessRuleException) as error:
        service.create(passenger, order_in("comfort"))
    assert error.value.error == "ACTIVE_ORDER_EXISTS"


def test_no_free_drivers(db, passenger):
    service = OrderService(db, Cache())
    service.create(passenger, order_in("business"))
    other = User(email="o@t.ru", password_hash="x$y", full_name="O", phone="+79000000001")
    db.add(other)
    db.commit()
    with pytest.raises(BusinessRuleException, match="No free drivers"):
        service.create(other, order_in("business"))


def test_lifecycle_and_driver_released(db, passenger):
    service = OrderService(db, Cache())
    order = service.create(passenger, order_in())
    service.change_status(admin(db), order.id, OrderStatus.IN_PROGRESS)
    done = service.change_status(admin(db), order.id, OrderStatus.COMPLETED)
    assert done.status == OrderStatus.COMPLETED and done.finished_at is not None
    assert done.driver.status == DriverStatus.FREE
    assert [e.event_type for e in db.query(OutboxEvent).order_by(OutboxEvent.id)] == \
        ["order.assigned", "order.in_progress", "order.completed"]
    with pytest.raises(BusinessRuleException, match="not allowed"):
        service.change_status(admin(db), order.id, OrderStatus.CANCELLED)


def test_passenger_permissions(db, passenger):
    service = OrderService(db, Cache())
    order = service.create(passenger, order_in())
    with pytest.raises(ForbiddenException):
        service.change_status(passenger, order.id, OrderStatus.IN_PROGRESS)
    service.change_status(admin(db), order.id, OrderStatus.IN_PROGRESS)
    with pytest.raises(BusinessRuleException) as error:
        service.change_status(passenger, order.id, OrderStatus.CANCELLED)
    assert error.value.error == "TRIP_STARTED"


def test_cancel_frees_driver_and_zeroes_price(db, passenger):
    service = OrderService(db, Cache())
    order = service.create(passenger, order_in())
    cancelled = service.change_status(passenger, order.id, OrderStatus.CANCELLED)
    assert cancelled.price == 0 and cancelled.driver.status == DriverStatus.FREE
    service.create(passenger, order_in())                          # теперь можно заказать снова


def test_surge_grows_with_demand(db, passenger):
    service = OrderService(db, Cache())
    assert service.current_surge() == 1.0
    for index, car_class in enumerate(["economy", "economy", "comfort"]):
        user = User(email=f"u{index}@t.ru", password_hash="x$y", full_name="U", phone="+79000000000")
        db.add(user)
        db.commit()
        service.create(user, order_in(car_class))
    assert service.current_surge() == 1.2                          # 3 из 5 заняты


def test_fleet_rules(db):
    fleet = FleetService(db, Cache())
    with pytest.raises(BusinessRuleException, match="already assigned"):
        fleet.create_driver(DriverIn(full_name="Новый", phone="+79009999999", license_number="77ZZ999999", car_id=1))
    car = fleet.create_car(CarIn(plate="Х999ХХ777", model="Lada Vesta", car_class=CarClass.ECONOMY, year=2022))
    driver = fleet.create_driver(DriverIn(full_name="Новый", phone="+79009999999", license_number="77ZZ999999",
                                          car_id=car.id))
    with pytest.raises(BusinessRuleException, match="already exists"):
        fleet.create_car(CarIn(plate="Х999ХХ777", model="Lada", car_class=CarClass.ECONOMY, year=2022))
    with pytest.raises(BusinessRuleException, match="only by order"):
        fleet.update_driver(driver.id, DriverUpdate(status=DriverStatus.BUSY))
    assert fleet.update_driver(driver.id, DriverUpdate(status=DriverStatus.OFFLINE)).status == DriverStatus.OFFLINE
    fleet.delete_driver(driver.id)
    with pytest.raises(EntityNotFoundException):
        fleet.get_driver(driver.id)


def test_busy_driver_cannot_be_deleted_or_changed(db, passenger):
    order = OrderService(db, Cache()).create(passenger, order_in())
    fleet = FleetService(db, Cache())
    with pytest.raises(BusinessRuleException, match="on a trip"):
        fleet.delete_driver(order.driver_id)
    with pytest.raises(BusinessRuleException, match="on a trip"):
        fleet.update_driver(order.driver_id, DriverUpdate(status=DriverStatus.OFFLINE))
    with pytest.raises(BusinessRuleException, match="on a trip"):
        fleet.delete_car(order.driver.car_id)


def test_driver_cache_and_invalidation(db):
    cache = Cache(fakeredis.FakeRedis(decode_responses=True))
    fleet = FleetService(db, cache)
    fleet.get_driver(1)
    fleet.get_driver(1)
    assert (cache.hits, cache.misses) == (1, 1)
    fleet.update_driver(1, DriverUpdate(rating=4.0))
    assert fleet.get_driver(1)["rating"] == 4.0                     # кэш сброшен после изменения


def test_cache_survives_redis_failure():
    class Broken:
        def __getattr__(self, name):
            raise ConnectionError("redis down")

    cache = Cache(Broken())
    cache.set("k", 1)
    cache.delete("k")
    assert cache.get("k") is None and cache.ping() is False
