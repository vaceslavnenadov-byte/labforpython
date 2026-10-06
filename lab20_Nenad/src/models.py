from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class CarClass(StrEnum):
    ECONOMY = "economy"
    COMFORT = "comfort"
    BUSINESS = "business"


class RideStatus(StrEnum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Driver(Base):
    __tablename__ = "drivers"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    car_plate: Mapped[str] = mapped_column(String(12), unique=True)
    car_class: Mapped[CarClass] = mapped_column(SAEnum(CarClass, native_enum=False))
    rides: Mapped[list["Ride"]] = relationship(back_populates="driver")


class Ride(Base):
    __tablename__ = "rides"
    __table_args__ = (CheckConstraint("distance_km > 0", name="ck_distance"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    passenger: Mapped[str] = mapped_column(String(120))
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"))
    pickup: Mapped[str] = mapped_column(String(200))
    destination: Mapped[str] = mapped_column(String(200))
    distance_km: Mapped[float] = mapped_column(Float)
    cost: Mapped[float] = mapped_column(Float)
    status: Mapped[RideStatus] = mapped_column(SAEnum(RideStatus, native_enum=False), default=RideStatus.CREATED)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    driver: Mapped[Driver] = relationship(back_populates="rides", lazy="joined")
