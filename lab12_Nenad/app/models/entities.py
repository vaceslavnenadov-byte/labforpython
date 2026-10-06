"""ORM-модели (SQLAlchemy 2.x, декларативный стиль с Mapped)."""

from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, Column, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Table, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class CarClass(str, Enum):
    ECONOMY = "economy"
    COMFORT = "comfort"
    BUSINESS = "business"


class DriverStatus(str, Enum):
    FREE = "free"
    BUSY = "busy"
    OFFLINE = "offline"


class TripStatus(str, Enum):
    CREATED = "created"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Связь многие-ко-многим: один водитель может работать на нескольких машинах, одна машина — у нескольких водителей
driver_cars = Table(
    "driver_cars",
    Base.metadata,
    Column("driver_id", ForeignKey("drivers.id", ondelete="CASCADE"), primary_key=True),
    Column("car_id", ForeignKey("cars.id", ondelete="CASCADE"), primary_key=True),
)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    email: Mapped[str | None] = mapped_column(String(120))
    registered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    trips: Mapped[list["Trip"]] = relationship(back_populates="client")

    def __repr__(self) -> str:
        return f"Client(id={self.id}, {self.full_name}, {self.phone})"


class Driver(Base):
    __tablename__ = "drivers"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_driver_rating"),
        CheckConstraint("experience_years >= 0", name="ck_driver_experience"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    license_number: Mapped[str] = mapped_column(String(20), unique=True)
    experience_years: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    status: Mapped[DriverStatus] = mapped_column(SAEnum(DriverStatus, native_enum=False), default=DriverStatus.FREE)

    trips: Mapped[list["Trip"]] = relationship(back_populates="driver")
    cars: Mapped[list["Car"]] = relationship(secondary=driver_cars, back_populates="drivers")

    def __repr__(self) -> str:
        return f"Driver(id={self.id}, {self.full_name}, {self.status.value}, ★{self.rating})"


class Car(Base):
    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(primary_key=True)
    plate: Mapped[str] = mapped_column(String(12), unique=True)
    model: Mapped[str] = mapped_column(String(60))
    car_class: Mapped[CarClass] = mapped_column(SAEnum(CarClass, native_enum=False))

    drivers: Mapped[list[Driver]] = relationship(secondary=driver_cars, back_populates="cars")

    def __repr__(self) -> str:
        return f"Car({self.plate}, {self.model}, {self.car_class.value})"


class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint("distance_km > 0", name="ck_trip_distance"),
        CheckConstraint("duration_min > 0", name="ck_trip_duration"),
        CheckConstraint("cost >= 0", name="ck_trip_cost"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="RESTRICT"))
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("drivers.id", ondelete="SET NULL"))
    car_id: Mapped[int | None] = mapped_column(ForeignKey("cars.id", ondelete="SET NULL"))
    pickup: Mapped[str] = mapped_column(String(200))
    destination: Mapped[str] = mapped_column(String(200))
    distance_km: Mapped[float] = mapped_column(Float)
    duration_min: Mapped[int] = mapped_column(Integer)
    car_class: Mapped[CarClass] = mapped_column(SAEnum(CarClass, native_enum=False))
    status: Mapped[TripStatus] = mapped_column(SAEnum(TripStatus, native_enum=False), default=TripStatus.CREATED)
    cost: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    client: Mapped[Client] = relationship(back_populates="trips")
    driver: Mapped[Driver | None] = relationship(back_populates="trips")
    car: Mapped[Car | None] = relationship()

    def __repr__(self) -> str:
        return (f"Trip(id={self.id}, {self.pickup} → {self.destination}, {self.distance_km} км, "
                f"{self.car_class.value}, {self.status.value}, {self.cost:.2f} руб.)")
