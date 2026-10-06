"""Order Service — заказы такси. Синхронно обращается к Passenger и Driver Service (Retry + Circuit Breaker),
публикует события OrderCreated / OrderStatusChanged в брокер."""

import os
from datetime import datetime
from enum import Enum

from fastapi import Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, Enum as SAEnum, Float, Integer, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from common.db import make_session_factory
from common.events import create_bus, make_event
from common.observability import setup
from common.resilience import CircuitOpenError, ServiceClient, ServiceUnavailableError

SERVICE = "order-service"
TARIFFS = {"economy": (99, 14), "comfort": (149, 19), "business": (299, 32)}


class OrderStatus(str, Enum):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


TRANSITIONS = {
    OrderStatus.ASSIGNED: {OrderStatus.IN_PROGRESS, OrderStatus.CANCELLED},
    OrderStatus.IN_PROGRESS: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    passenger_id: Mapped[int] = mapped_column(Integer)     # ссылка на данные другого сервиса — без FK
    driver_id: Mapped[int] = mapped_column(Integer)
    pickup: Mapped[str] = mapped_column(String(200))
    destination: Mapped[str] = mapped_column(String(200))
    distance_km: Mapped[float] = mapped_column(Float)
    car_class: Mapped[str] = mapped_column(String(10))
    status: Mapped[OrderStatus] = mapped_column(SAEnum(OrderStatus, native_enum=False), default=OrderStatus.ASSIGNED)
    cost: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class OrderIn(BaseModel):
    passenger_id: int = Field(gt=0)
    pickup: str = Field(min_length=2, max_length=200)
    destination: str = Field(min_length=2, max_length=200)
    distance_km: float = Field(gt=0, le=500)
    car_class: str = Field(pattern="^(economy|comfort|business)$")


class OrderUpdate(BaseModel):
    pickup: str = Field(min_length=2, max_length=200)
    destination: str = Field(min_length=2, max_length=200)
    distance_km: float = Field(gt=0, le=500)


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    passenger_id: int
    driver_id: int
    pickup: str
    destination: str
    distance_km: float
    car_class: str
    status: OrderStatus
    cost: float
    created_at: datetime


class StatusIn(BaseModel):
    status: OrderStatus


def calculate_cost(car_class: str, distance_km: float) -> float:
    base, per_km = TARIFFS[car_class]
    return round(base + per_km * distance_km, 2)


def create_app(database_url: str | None = None, bus=None, passengers: ServiceClient | None = None,
               drivers: ServiceClient | None = None) -> FastAPI:
    app = FastAPI(title="Order Service")
    logger = setup(app, SERVICE)
    factory = make_session_factory(database_url or os.getenv("DATABASE_URL", "sqlite:///orders.db"))
    Base.metadata.create_all(factory.kw["bind"])
    bus = bus or create_bus(os.getenv("BROKER_URL", "memory://"))
    passengers = passengers or ServiceClient("passenger-service", os.getenv("PASSENGER_SERVICE_URL", "http://localhost:8001"))
    drivers = drivers or ServiceClient("driver-service", os.getenv("DRIVER_SERVICE_URL", "http://localhost:8002"))

    def db():
        with factory() as session:
            yield session

    def get_or_404(session: Session, order_id: int) -> Order:
        order = session.get(Order, order_id)
        if order is None:
            raise HTTPException(404, f"Order {order_id} not found")
        return order

    def publish(event_type: str, order: Order) -> None:
        payload = {"order_id": order.id, "passenger_id": order.passenger_id, "driver_id": order.driver_id,
                   "status": order.status.value, "cost": order.cost, "route": f"{order.pickup} → {order.destination}"}
        try:
            bus.publish(make_event(event_type, payload, SERVICE))
        except Exception as error:   # брокер недоступен — заказ уже сохранён, событие теряется (см. Outbox в README)
            logger.error("publish %s failed: %s", event_type, error)

    @app.get("/orders", response_model=list[OrderOut])
    def list_orders(passenger_id: int | None = None, status: OrderStatus | None = None, session: Session = Depends(db)):
        stmt = select(Order).order_by(Order.id.desc())
        if passenger_id:
            stmt = stmt.where(Order.passenger_id == passenger_id)
        if status:
            stmt = stmt.where(Order.status == status)
        return session.scalars(stmt).all()

    @app.get("/orders/{order_id}", response_model=OrderOut)
    def get_order(order_id: int, session: Session = Depends(db)):
        return get_or_404(session, order_id)

    @app.post("/orders", response_model=OrderOut, status_code=201)
    def create_order(data: OrderIn, session: Session = Depends(db)):
        # 1. синхронная проверка пассажира (Retry + Circuit Breaker)
        try:
            response = passengers.request("GET", f"/passengers/{data.passenger_id}")
        except CircuitOpenError as error:
            raise HTTPException(503, str(error)) from None
        except ServiceUnavailableError as error:
            raise HTTPException(503, str(error)) from None
        if response.status_code == 404:
            raise HTTPException(400, f"Passenger {data.passenger_id} does not exist")
        # 2. назначение водителя
        try:
            response = drivers.request("POST", "/drivers/assign", json={"car_class": data.car_class})
        except ServiceUnavailableError as error:
            raise HTTPException(503, str(error)) from None
        if response.status_code == 409:
            raise HTTPException(409, response.json()["detail"])
        driver = response.json()
        # 3. сохранение заказа; при ошибке — компенсирующее действие (Saga): освобождаем водителя
        order = Order(**data.model_dump(), driver_id=driver["id"], cost=calculate_cost(data.car_class, data.distance_km))
        try:
            session.add(order)
            session.commit()
        except Exception:
            session.rollback()
            logger.error("saving order failed, compensating: release driver %s", driver["id"])
            try:
                drivers.request("POST", f"/drivers/{driver['id']}/release")
            except ServiceUnavailableError:
                logger.error("compensation failed for driver %s", driver["id"])
            raise HTTPException(500, "Order was not saved") from None
        publish("OrderCreated", order)
        return order

    @app.put("/orders/{order_id}", response_model=OrderOut)
    def update_order(order_id: int, data: OrderUpdate, session: Session = Depends(db)):
        order = get_or_404(session, order_id)
        if order.status != OrderStatus.ASSIGNED:
            raise HTTPException(409, "Only an order that has not started can be changed")
        for key, value in data.model_dump().items():
            setattr(order, key, value)
        order.cost = calculate_cost(order.car_class, order.distance_km)
        session.commit()
        return order

    @app.patch("/orders/{order_id}/status", response_model=OrderOut)
    def change_status(order_id: int, data: StatusIn, session: Session = Depends(db)):
        order = get_or_404(session, order_id)
        if data.status not in TRANSITIONS[order.status]:
            raise HTTPException(409, f"Transition {order.status.value} -> {data.status.value} is not allowed")
        order.status = data.status
        if order.status == OrderStatus.CANCELLED:
            order.cost = 0
        session.commit()
        publish("OrderStatusChanged", order)          # водитель освобождается асинхронно по событию
        return order

    @app.delete("/orders/{order_id}", status_code=204)
    def delete_order(order_id: int, session: Session = Depends(db)):
        order = get_or_404(session, order_id)
        if order.status not in (OrderStatus.CANCELLED, OrderStatus.COMPLETED):
            raise HTTPException(409, "Cancel the order before deleting")
        session.delete(order)
        session.commit()
        return Response(status_code=204)

    @app.get("/circuit", tags=["service"])
    def circuit_state():
        return {"passenger-service": passengers.breaker.state.value, "driver-service": drivers.breaker.state.value}

    app.state.bus, app.state.passengers, app.state.drivers = bus, passengers, drivers
    return app


app = create_app() if os.getenv("SERVICE_AUTOSTART", "1") == "1" else None
