"""Driver Service — водители и их статусы. Собственная БД, REST API, подписка на события заказов."""

import os
import threading
from enum import Enum

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Enum as SAEnum, Float, Integer, String, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from common.db import make_session_factory
from common.events import create_bus
from common.observability import setup

SERVICE = "driver-service"


class CarClass(str, Enum):
    ECONOMY = "economy"
    COMFORT = "comfort"
    BUSINESS = "business"


class DriverStatus(str, Enum):
    FREE = "free"
    BUSY = "busy"
    OFFLINE = "offline"


class Base(DeclarativeBase):
    pass


class Driver(Base):
    __tablename__ = "drivers"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    car: Mapped[str] = mapped_column(String(80))
    car_class: Mapped[CarClass] = mapped_column(SAEnum(CarClass, native_enum=False))
    status: Mapped[DriverStatus] = mapped_column(SAEnum(DriverStatus, native_enum=False), default=DriverStatus.FREE)
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    trips_count: Mapped[int] = mapped_column(Integer, default=0)


class DriverIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(pattern=r"^\+?\d{10,15}$")
    car: str = Field(min_length=2, max_length=80)
    car_class: CarClass


class DriverOut(DriverIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: DriverStatus
    rating: float
    trips_count: int


class AssignRequest(BaseModel):
    car_class: CarClass
    order_id: int | None = None


class StatusRequest(BaseModel):
    status: DriverStatus


def create_app(database_url: str | None = None, bus=None) -> FastAPI:
    app = FastAPI(title="Driver Service")
    logger = setup(app, SERVICE)
    factory = make_session_factory(database_url or os.getenv("DATABASE_URL", "sqlite:///drivers.db"))
    Base.metadata.create_all(factory.kw["bind"])
    bus = bus or create_bus(os.getenv("BROKER_URL", "memory://"))
    assign_lock = threading.Lock()   # не отдать одного водителя двум заказам

    def db():
        with factory() as session:
            yield session

    def get_or_404(session: Session, driver_id: int) -> Driver:
        driver = session.get(Driver, driver_id)
        if driver is None:
            raise HTTPException(404, f"Driver {driver_id} not found")
        return driver

    @app.get("/drivers", response_model=list[DriverOut])
    def list_drivers(status: DriverStatus | None = None, car_class: CarClass | None = None,
                     session: Session = Depends(db)):
        stmt = select(Driver).order_by(Driver.id)
        if status:
            stmt = stmt.where(Driver.status == status)
        if car_class:
            stmt = stmt.where(Driver.car_class == car_class)
        return session.scalars(stmt).all()

    @app.get("/drivers/{driver_id}", response_model=DriverOut)
    def get_driver(driver_id: int, session: Session = Depends(db)):
        return get_or_404(session, driver_id)

    @app.post("/drivers", response_model=DriverOut, status_code=201)
    def create_driver(data: DriverIn, session: Session = Depends(db)):
        driver = Driver(**data.model_dump())
        session.add(driver)
        try:
            session.commit()
        except IntegrityError:
            raise HTTPException(409, "Phone already registered") from None
        return driver

    @app.put("/drivers/{driver_id}", response_model=DriverOut)
    def update_driver(driver_id: int, data: DriverIn, session: Session = Depends(db)):
        driver = get_or_404(session, driver_id)
        for key, value in data.model_dump().items():
            setattr(driver, key, value)
        session.commit()
        return driver

    @app.delete("/drivers/{driver_id}", status_code=204)
    def delete_driver(driver_id: int, session: Session = Depends(db)):
        driver = get_or_404(session, driver_id)
        if driver.status == DriverStatus.BUSY:
            raise HTTPException(409, "Driver is on a trip")
        session.delete(driver)
        session.commit()
        return Response(status_code=204)

    @app.patch("/drivers/{driver_id}/status", response_model=DriverOut)
    def set_status(driver_id: int, data: StatusRequest, session: Session = Depends(db)):
        driver = get_or_404(session, driver_id)
        driver.status = data.status
        session.commit()
        return driver

    @app.post("/drivers/assign", response_model=DriverOut)
    def assign(data: AssignRequest, session: Session = Depends(db)):
        """Выбрать лучшего свободного водителя нужного класса и пометить его занятым."""
        with assign_lock:
            driver = session.scalars(select(Driver).where(Driver.status == DriverStatus.FREE,
                                                          Driver.car_class == data.car_class)
                                     .order_by(Driver.rating.desc()).limit(1)).first()
            if driver is None:
                raise HTTPException(409, f"No free drivers of class {data.car_class.value}")
            driver.status = DriverStatus.BUSY
            session.commit()
            logger.info("driver %s assigned to order %s", driver.id, data.order_id)
            return driver

    @app.post("/drivers/{driver_id}/release", response_model=DriverOut)
    def release(driver_id: int, session: Session = Depends(db)):
        """Компенсирующее действие Saga и освобождение после поездки (идемпотентно)."""
        driver = get_or_404(session, driver_id)
        if driver.status == DriverStatus.BUSY:
            driver.status = DriverStatus.FREE
            session.commit()
        return driver

    def on_event(event: dict) -> None:
        payload = event["payload"]
        if event["type"] != "OrderStatusChanged" or payload.get("status") not in ("completed", "cancelled"):
            return
        with factory() as session:
            driver = session.get(Driver, payload.get("driver_id") or 0)
            if driver:
                driver.status = DriverStatus.FREE
                if payload["status"] == "completed":
                    driver.trips_count += 1
                session.commit()
                logger.info("event %s: driver %s is free", event["type"], driver.id)

    bus.subscribe(SERVICE, on_event)
    app.state.bus = bus
    return app


app = create_app() if os.getenv("SERVICE_AUTOSTART", "1") == "1" else None
