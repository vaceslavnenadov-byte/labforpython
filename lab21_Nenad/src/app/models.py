"""ORM-модели: пользователь (пассажир/администратор), автомобиль, водитель, заказ, уведомление, outbox."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Role(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"


class CarClass(StrEnum):
    ECONOMY = "economy"
    COMFORT = "comfort"
    BUSINESS = "business"


class DriverStatus(StrEnum):
    FREE = "free"
    BUSY = "busy"
    OFFLINE = "offline"


class OrderStatus(StrEnum):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


def enum(cls):
    return SAEnum(cls, native_enum=False, length=20)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20))
    role: Mapped[Role] = mapped_column(enum(Role), default=Role.USER)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    orders: Mapped[list["Order"]] = relationship(back_populates="passenger")


class Car(Base):
    __tablename__ = "cars"
    __table_args__ = (CheckConstraint("year BETWEEN 1990 AND 2100", name="ck_car_year"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    plate: Mapped[str] = mapped_column(String(12), unique=True)
    model: Mapped[str] = mapped_column(String(80))
    car_class: Mapped[CarClass] = mapped_column(enum(CarClass))
    year: Mapped[int] = mapped_column(Integer)
    driver: Mapped["Driver | None"] = relationship(back_populates="car")


class Driver(Base):
    __tablename__ = "drivers"
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="ck_driver_rating"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    license_number: Mapped[str] = mapped_column(String(20), unique=True)
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    status: Mapped[DriverStatus] = mapped_column(enum(DriverStatus), default=DriverStatus.FREE, index=True)
    car_id: Mapped[int | None] = mapped_column(ForeignKey("cars.id", ondelete="SET NULL"), unique=True)
    car: Mapped[Car | None] = relationship(back_populates="driver", lazy="joined")
    orders: Mapped[list["Order"]] = relationship(back_populates="driver")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("distance_km > 0", name="ck_order_distance"),
        CheckConstraint("price >= 0", name="ck_order_price"),
        Index("ix_orders_passenger_status", "passenger_id", "status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    passenger_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("drivers.id", ondelete="SET NULL"))
    pickup: Mapped[str] = mapped_column(String(200))
    destination: Mapped[str] = mapped_column(String(200))
    distance_km: Mapped[float] = mapped_column(Float)
    car_class: Mapped[CarClass] = mapped_column(enum(CarClass))
    status: Mapped[OrderStatus] = mapped_column(enum(OrderStatus), default=OrderStatus.ASSIGNED, index=True)
    price: Mapped[float] = mapped_column(Float)
    surge: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    passenger: Mapped[User] = relationship(back_populates="orders")
    driver: Mapped[Driver | None] = relationship(back_populates="orders", lazy="joined")


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(40), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class OutboxEvent(Base):
    """Transactional Outbox: событие пишется в той же транзакции, что и изменение заказа."""
    __tablename__ = "outbox"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(40), unique=True)
    event_type: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON)
    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
