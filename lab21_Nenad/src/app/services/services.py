"""Бизнес-логика. Правила:
1. У пассажира может быть только один активный заказ.
2. Водитель назначается автоматически: свободный, с машиной нужного класса, с лучшим рейтингом; становится занятым.
3. Статусы меняются только по допустимым переходам; пассажир может отменить заказ только до начала поездки.
4. Стоимость зависит от спроса (доля занятых водителей).
5. Нельзя удалить водителя во время поездки и закрепить одну машину за двумя водителями.
"""

import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from src.app.cache import Cache
from src.app.exceptions import (
    AuthException,
    BusinessRuleException,
    EntityNotFoundException,
    ForbiddenException,
    ValidationException,
)
from src.app.models import Car, CarClass, Driver, DriverStatus, Order, OrderStatus, OutboxEvent, Role, User
from src.app.repositories.repositories import (
    CarRepository,
    DriverRepository,
    NotificationRepository,
    OrderRepository,
    OutboxRepository,
    UserRepository,
)
from src.app.schemas import CarIn, DriverIn, DriverUpdate, OrderIn, RegisterIn
from src.app.security import create_token, hash_password, verify_password
from src.app.services.pricing import calculate_price, surge_multiplier

logger = logging.getLogger("taxi.service")

TRANSITIONS = {
    OrderStatus.ASSIGNED: {OrderStatus.IN_PROGRESS, OrderStatus.CANCELLED},
    OrderStatus.IN_PROGRESS: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}


class AuthService:
    def __init__(self, db: Session, secret: str, expire_minutes: int) -> None:
        self.db, self.users = db, UserRepository(db)
        self.secret, self.expire_minutes = secret, expire_minutes

    def register(self, data: RegisterIn, role: Role = Role.USER) -> User:
        if self.users.by_email(data.email):
            raise BusinessRuleException(f"User {data.email} already exists", "USER_EXISTS")
        user = self.users.add(User(email=data.email.lower(), password_hash=hash_password(data.password),
                                   full_name=data.full_name, phone=data.phone, role=role))
        self.db.commit()
        logger.info("registered user %s (%s)", user.id, role.value)
        return user

    def login(self, email: str, password: str) -> str:
        user = self.users.by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthException("Invalid email or password")
        return create_token(user.id, user.role.value, self.secret, self.expire_minutes)


class FleetService:
    """Автомобили и водители (управляет администратор)."""

    def __init__(self, db: Session, cache: Cache) -> None:
        self.db, self.cache = db, cache
        self.cars, self.drivers = CarRepository(db), DriverRepository(db)

    def _invalidate(self, driver_id: int | None = None) -> None:
        self.cache.delete("stats", *( [f"driver:{driver_id}"] if driver_id else []))

    # автомобили
    def list_cars(self) -> list[Car]:
        return self.cars.all()

    def create_car(self, data: CarIn) -> Car:
        if self.cars.by_plate(data.plate):
            raise BusinessRuleException(f"Car {data.plate} already exists", "CAR_EXISTS")
        car = self.cars.add(Car(**data.model_dump()))
        self.db.commit()
        return car

    def delete_car(self, car_id: int) -> None:
        car = self.cars.get(car_id)
        if car is None:
            raise EntityNotFoundException(f"Car {car_id} not found", "CAR_NOT_FOUND")
        if car.driver and car.driver.status == DriverStatus.BUSY:
            raise BusinessRuleException("Car is on a trip", "CAR_BUSY")
        self.db.delete(car)
        self.db.commit()

    # водители
    def get_driver(self, driver_id: int) -> dict:
        from src.app.schemas import DriverOut
        cached = self.cache.get(f"driver:{driver_id}")
        if cached is not None:
            return cached
        driver = self.drivers.get(driver_id)
        if driver is None:
            raise EntityNotFoundException(f"Driver {driver_id} not found", "DRIVER_NOT_FOUND")
        data = DriverOut.model_validate(driver).model_dump(mode="json")
        self.cache.set(f"driver:{driver_id}", data)
        return data

    def list_drivers(self, status: DriverStatus | None, car_class: CarClass | None, sort: str) -> list[Driver]:
        if sort not in ("rating", "name"):
            raise ValidationException("sort must be 'rating' or 'name'")
        return self.drivers.search(status, car_class, sort)

    def _check_car(self, car_id: int | None, driver_id: int | None = None) -> None:
        if car_id is None:
            return
        car = self.cars.get(car_id)
        if car is None:
            raise EntityNotFoundException(f"Car {car_id} not found", "CAR_NOT_FOUND")
        if car.driver and car.driver.id != driver_id:
            raise BusinessRuleException(f"Car {car.plate} is already assigned to another driver", "CAR_TAKEN")

    def create_driver(self, data: DriverIn) -> Driver:
        if self.drivers.by_phone_or_license(data.phone, data.license_number):
            raise BusinessRuleException("Driver with this phone or license already exists", "DRIVER_EXISTS")
        self._check_car(data.car_id)
        driver = self.drivers.add(Driver(**data.model_dump()))
        self.db.commit()
        self._invalidate()
        return driver

    def update_driver(self, driver_id: int, data: DriverUpdate) -> Driver:
        driver = self.drivers.get(driver_id)
        if driver is None:
            raise EntityNotFoundException(f"Driver {driver_id} not found", "DRIVER_NOT_FOUND")
        fields = data.model_dump(exclude_unset=True)
        if "status" in fields and driver.status == DriverStatus.BUSY and fields["status"] != DriverStatus.BUSY:
            raise BusinessRuleException("Driver is on a trip; status changes automatically", "DRIVER_BUSY")
        if fields.get("status") == DriverStatus.BUSY:
            raise BusinessRuleException("Status 'busy' is set only by order assignment", "DRIVER_BUSY")
        if "car_id" in fields:
            self._check_car(fields["car_id"], driver_id)
        for key, value in fields.items():
            setattr(driver, key, value)
        self.db.commit()
        self.db.refresh(driver)
        self._invalidate(driver_id)
        return driver

    def delete_driver(self, driver_id: int) -> None:
        driver = self.drivers.get(driver_id)
        if driver is None:
            raise EntityNotFoundException(f"Driver {driver_id} not found", "DRIVER_NOT_FOUND")
        if driver.status == DriverStatus.BUSY:
            raise BusinessRuleException("Driver is on a trip", "DRIVER_BUSY")
        self.db.delete(driver)
        self.db.commit()
        self._invalidate(driver_id)


class OrderService:
    def __init__(self, db: Session, cache: Cache) -> None:
        self.db, self.cache = db, cache
        self.orders, self.drivers = OrderRepository(db), DriverRepository(db)
        self.outbox = OutboxRepository(db)

    def _event(self, event_type: str, order: Order) -> None:
        """Событие пишется в outbox в той же транзакции, что и изменение заказа."""
        self.outbox.add(OutboxEvent(event_id=uuid.uuid4().hex, event_type=event_type, payload={
            "order_id": order.id, "passenger_id": order.passenger_id, "driver_id": order.driver_id,
            "status": order.status.value, "price": order.price, "route": f"{order.pickup} → {order.destination}",
            "driver_name": order.driver.full_name if order.driver else None,
            "car": f"{order.driver.car.model} {order.driver.car.plate}" if order.driver and order.driver.car else None,
        }))

    def current_surge(self) -> float:
        counts = self.drivers.count_by_status()
        online = counts.get("free", 0) + counts.get("busy", 0)
        return surge_multiplier(counts.get("busy", 0), online)

    def quote(self, car_class: CarClass, distance_km: float) -> dict:
        surge = self.current_surge()
        return {"car_class": car_class, "distance_km": distance_km, "surge": surge,
                "price": calculate_price(car_class, distance_km, surge)}

    def create(self, passenger: User, data: OrderIn) -> Order:
        if self.orders.active_for_passenger(passenger.id):                       # правило 1
            raise BusinessRuleException("You already have an active order", "ACTIVE_ORDER_EXISTS")
        surge = self.current_surge()
        driver = self.drivers.find_free(data.car_class)                          # правило 2
        if driver is None:
            raise BusinessRuleException(f"No free drivers of class {data.car_class.value}", "NO_FREE_DRIVERS")
        order = self.orders.add(Order(
            passenger_id=passenger.id, driver_id=driver.id, pickup=data.pickup, destination=data.destination,
            distance_km=data.distance_km, car_class=data.car_class, surge=surge,
            price=calculate_price(data.car_class, data.distance_km, surge)))     # правило 4
        driver.status = DriverStatus.BUSY
        self.db.flush()
        self.db.refresh(order)
        self._event("order.assigned", order)
        self.db.commit()                                                         # заказ + водитель + событие — атомарно
        self.cache.delete("stats", f"driver:{driver.id}")
        logger.info("order %s created: passenger=%s driver=%s price=%.2f",
                    order.id, passenger.id, driver.id, order.price)
        return order

    def get(self, user: User, order_id: int) -> Order:
        order = self.orders.get(order_id)
        if order is None or (user.role != Role.ADMIN and order.passenger_id != user.id):
            raise EntityNotFoundException(f"Order {order_id} not found", "ORDER_NOT_FOUND")
        return order

    def search(self, user: User, status: OrderStatus | None, text: str | None, sort: str, order: str,
               skip: int, limit: int) -> tuple[list[Order], int]:
        if sort not in ("created_at", "price", "distance"):
            raise ValidationException("sort must be created_at, price or distance")
        passenger_id = None if user.role == Role.ADMIN else user.id
        return self.orders.search(passenger_id=passenger_id, status=status, text=text, sort=sort, order=order,
                                  skip=skip, limit=limit)

    def change_status(self, user: User, order_id: int, new_status: OrderStatus) -> Order:
        order = self.get(user, order_id)
        if new_status not in TRANSITIONS[order.status]:                          # правило 3
            raise BusinessRuleException(f"Transition {order.status.value} -> {new_status.value} is not allowed",
                                        "INVALID_TRANSITION")
        if user.role != Role.ADMIN:
            if new_status != OrderStatus.CANCELLED:
                raise ForbiddenException("Only dispatcher (ADMIN) can start or complete a trip")
            if order.status != OrderStatus.ASSIGNED:
                raise BusinessRuleException("Trip already started and cannot be cancelled by passenger",
                                            "TRIP_STARTED")
        order.status = new_status
        if new_status in (OrderStatus.COMPLETED, OrderStatus.CANCELLED):
            order.finished_at = datetime.now()
            if new_status == OrderStatus.CANCELLED:
                order.price = 0
            if order.driver:
                order.driver.status = DriverStatus.FREE
        self._event(f"order.{new_status.value}", order)
        self.db.commit()
        self.cache.delete("stats", *([f"driver:{order.driver_id}"] if order.driver_id else []))
        logger.info("order %s -> %s by user %s", order.id, new_status.value, user.id)
        return order

    def delete(self, order_id: int) -> None:
        order = self.orders.get(order_id)
        if order is None:
            raise EntityNotFoundException(f"Order {order_id} not found", "ORDER_NOT_FOUND")
        if order.status in (OrderStatus.ASSIGNED, OrderStatus.IN_PROGRESS):
            raise BusinessRuleException("Active order cannot be deleted", "ORDER_ACTIVE")
        self.orders.delete(order)
        self.db.commit()

    def statistics(self) -> dict:
        cached = self.cache.get("stats")
        if cached is not None:
            return {**cached, "source": "cache"}
        stats = self.orders.statistics()
        stats["drivers_by_status"] = self.drivers.count_by_status()
        stats["surge"] = self.current_surge()
        self.cache.set("stats", stats, ttl=30)
        return {**stats, "source": "database"}


def notifications_for(db: Session, user: User):
    return NotificationRepository(db).for_user(user.id)
