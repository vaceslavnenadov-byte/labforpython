"""Сущности: станция, поезд, пользователь (пассажир), билет."""

from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum as SAEnum, Float, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class WagonType(str, Enum):
    SEATED = "seated"
    COUPE = "coupe"
    SV = "sv"

    @property
    def title(self) -> str:
        return {"seated": "Сидячий", "coupe": "Купе", "sv": "СВ"}[self.value]

    @property
    def coefficient(self) -> float:
        return {"seated": 1.0, "coupe": 1.8, "sv": 3.0}[self.value]


class TicketStatus(str, Enum):
    ACTIVE = "active"
    RETURNED = "returned"


class Station(Base):
    __tablename__ = "stations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    city: Mapped[str] = mapped_column(String(100), index=True)


class Train(Base):
    __tablename__ = "trains"
    __table_args__ = (CheckConstraint("base_price > 0", name="ck_price"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    from_station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"))
    to_station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"))
    departure: Mapped[datetime] = mapped_column(DateTime)
    arrival: Mapped[datetime] = mapped_column(DateTime)
    base_price: Mapped[float] = mapped_column(Float)
    seats_seated: Mapped[int] = mapped_column(Integer, default=0)
    seats_coupe: Mapped[int] = mapped_column(Integer, default=0)
    seats_sv: Mapped[int] = mapped_column(Integer, default=0)

    from_station: Mapped[Station] = relationship(foreign_keys=[from_station_id], lazy="joined")
    to_station: Mapped[Station] = relationship(foreign_keys=[to_station_id], lazy="joined")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="train")

    def capacity(self, wagon_type: WagonType) -> int:
        return getattr(self, f"seats_{wagon_type.value}")

    def price(self, wagon_type: WagonType) -> float:
        return round(self.base_price * wagon_type.coefficient, 2)

    @property
    def title(self) -> str:
        return f"{self.number} «{self.name}»"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str] = mapped_column(String(150))
    is_admin: Mapped[bool] = mapped_column(default=False)
    messages_count: Mapped[int] = mapped_column(Integer, default=0)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="user")


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint("seat >= 1", name="ck_seat"),
        # одно место в вагоне данного типа — один действующий билет
        Index("ux_active_seat", "train_id", "wagon_type", "seat", unique=True,
              sqlite_where=text("status = 'active'"),
              postgresql_where=text("status = 'active'")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    train_id: Mapped[int] = mapped_column(ForeignKey("trains.id"))
    wagon_type: Mapped[WagonType] = mapped_column(SAEnum(WagonType, native_enum=False))
    seat: Mapped[int] = mapped_column(Integer)
    passenger_name: Mapped[str] = mapped_column(String(150))
    price: Mapped[float] = mapped_column(Float)
    status: Mapped[TicketStatus] = mapped_column(SAEnum(TicketStatus, native_enum=False), default=TicketStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    user: Mapped[User] = relationship(back_populates="tickets")
    train: Mapped[Train] = relationship(back_populates="tickets", lazy="joined")
