from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CarClass(str, Enum):
    ECONOMY = "economy"
    COMFORT = "comfort"
    BUSINESS = "business"

    @property
    def title(self) -> str:
        return {"economy": "Эконом", "comfort": "Комфорт", "business": "Бизнес"}[self.value]


class TripStatus(str, Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    @property
    def title(self) -> str:
        return {"created": "Создана", "in_progress": "В пути", "completed": "Завершена",
                "cancelled": "Отменена"}[self.value]


class Driver(Base):
    __tablename__ = "drivers"
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="ck_rating"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    car_model: Mapped[str] = mapped_column(String(60))
    car_plate: Mapped[str] = mapped_column(String(12), unique=True)
    car_class: Mapped[CarClass] = mapped_column(SAEnum(CarClass, native_enum=False))
    rating: Mapped[float] = mapped_column(Float, default=5.0)

    trips: Mapped[list["Trip"]] = relationship(back_populates="driver")


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    email: Mapped[str | None] = mapped_column(String(120))

    trips: Mapped[list["Trip"]] = relationship(back_populates="client")


class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint("distance_km > 0", name="ck_distance"),
        CheckConstraint("duration_min > 0", name="ck_duration"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="RESTRICT"))
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id", ondelete="RESTRICT"))
    pickup: Mapped[str] = mapped_column(String(200))
    destination: Mapped[str] = mapped_column(String(200))
    distance_km: Mapped[float] = mapped_column(Float)
    duration_min: Mapped[int] = mapped_column(Integer)
    cost: Mapped[float] = mapped_column(Float)
    status: Mapped[TripStatus] = mapped_column(SAEnum(TripStatus, native_enum=False), default=TripStatus.CREATED)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    client: Mapped[Client] = relationship(back_populates="trips")
    driver: Mapped[Driver] = relationship(back_populates="trips")

    def to_dict(self) -> dict:
        return {"id": self.id, "client_id": self.client_id, "client": self.client.full_name,
                "driver_id": self.driver_id, "driver": self.driver.full_name, "car_class": self.driver.car_class.value,
                "pickup": self.pickup, "destination": self.destination, "distance_km": self.distance_km,
                "duration_min": self.duration_min, "cost": self.cost, "status": self.status.value,
                "created_at": self.created_at.isoformat(timespec="minutes")}
