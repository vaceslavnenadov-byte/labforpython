from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, CheckConstraint, DateTime, Enum as SAEnum, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TrainStatus(str, Enum):
    SCHEDULED = "scheduled"
    BOARDING = "boarding"
    DEPARTED = "departed"
    ARRIVED = "arrived"
    CANCELLED = "cancelled"


class Train(Base):
    __tablename__ = "trains"
    __table_args__ = (
        CheckConstraint("wagons_count > 0", name="ck_wagons_positive"),
        CheckConstraint("price > 0", name="ck_price_positive"),
        CheckConstraint("arrival_time > departure_time", name="ck_time_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    route: Mapped[str] = mapped_column(String(120), index=True)
    stations: Mapped[list[str]] = mapped_column(JSON, default=list)
    departure_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    arrival_time: Mapped[datetime] = mapped_column(DateTime)
    wagons_count: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float)
    status: Mapped[TrainStatus] = mapped_column(SAEnum(TrainStatus, native_enum=False), default=TrainStatus.SCHEDULED)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(10), default="USER")
