"""Passenger Service — пассажиры. Собственная БД (DATABASE_URL), REST API, подписка на события заказов."""

import os
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, Float, Integer, String, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from common.db import make_session_factory
from common.events import create_bus
from common.observability import setup

SERVICE = "passenger-service"


class Base(DeclarativeBase):
    pass


class Passenger(Base):
    __tablename__ = "passengers"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    trips_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PassengerIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(pattern=r"^\+?\d{10,15}$")


class PassengerOut(PassengerIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rating: float
    trips_count: int


def create_app(database_url: str | None = None, bus=None) -> FastAPI:
    app = FastAPI(title="Passenger Service")
    logger = setup(app, SERVICE)
    factory = make_session_factory(database_url or os.getenv("DATABASE_URL", "sqlite:///passengers.db"))
    Base.metadata.create_all(factory.kw["bind"])
    bus = bus or create_bus(os.getenv("BROKER_URL", "memory://"))

    def db():
        with factory() as session:
            yield session

    def get_or_404(session: Session, passenger_id: int) -> Passenger:
        passenger = session.get(Passenger, passenger_id)
        if passenger is None:
            raise HTTPException(404, f"Passenger {passenger_id} not found")
        return passenger

    @app.get("/passengers", response_model=list[PassengerOut])
    def list_passengers(session: Session = Depends(db)):
        return session.scalars(select(Passenger).order_by(Passenger.id)).all()

    @app.get("/passengers/{passenger_id}", response_model=PassengerOut)
    def get_passenger(passenger_id: int, session: Session = Depends(db)):
        return get_or_404(session, passenger_id)

    @app.post("/passengers", response_model=PassengerOut, status_code=201)
    def create_passenger(data: PassengerIn, session: Session = Depends(db)):
        passenger = Passenger(**data.model_dump())
        session.add(passenger)
        try:
            session.commit()
        except IntegrityError:
            raise HTTPException(409, "Phone already registered") from None
        return passenger

    @app.put("/passengers/{passenger_id}", response_model=PassengerOut)
    def update_passenger(passenger_id: int, data: PassengerIn, session: Session = Depends(db)):
        passenger = get_or_404(session, passenger_id)
        for key, value in data.model_dump().items():
            setattr(passenger, key, value)
        try:
            session.commit()
        except IntegrityError:
            raise HTTPException(409, "Phone already registered") from None
        return passenger

    @app.delete("/passengers/{passenger_id}", status_code=204)
    def delete_passenger(passenger_id: int, session: Session = Depends(db)):
        session.delete(get_or_404(session, passenger_id))
        session.commit()
        return Response(status_code=204)

    def on_event(event: dict) -> None:
        """Асинхронно: после завершения поездки увеличиваем счётчик поездок пассажира."""
        payload = event["payload"]
        if event["type"] == "OrderStatusChanged" and payload.get("status") == "completed":
            with factory() as session:
                passenger = session.get(Passenger, payload["passenger_id"])
                if passenger:
                    passenger.trips_count += 1
                    session.commit()
                    logger.info("event %s: passenger %s trips=%s", event["type"], passenger.id, passenger.trips_count)

    bus.subscribe(SERVICE, on_event)
    app.state.bus = bus
    return app


app = create_app() if os.getenv("SERVICE_AUTOSTART", "1") == "1" else None
