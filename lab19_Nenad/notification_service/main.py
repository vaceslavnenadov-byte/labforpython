"""Notification Service — получает события из брокера и формирует уведомления пассажирам."""

import os
from datetime import datetime

from fastapi import Depends, FastAPI
from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, Integer, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from common.db import make_session_factory
from common.events import create_bus
from common.observability import setup

SERVICE = "notification-service"
TEXTS = {
    "OrderCreated": "Водитель назначен на поездку {route}. Стоимость {cost} ₽.",
    "in_progress": "Поездка {route} началась.",
    "completed": "Поездка {route} завершена. К оплате {cost} ₽. Спасибо!",
    "cancelled": "Заказ {route} отменён.",
}


class Base(DeclarativeBase):
    pass


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(32), unique=True)    # идемпотентность: событие обрабатывается один раз
    passenger_id: Mapped[int] = mapped_column(Integer)
    order_id: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    passenger_id: int
    order_id: int
    text: str
    created_at: datetime


def create_app(database_url: str | None = None, bus=None) -> FastAPI:
    app = FastAPI(title="Notification Service")
    logger = setup(app, SERVICE)
    factory = make_session_factory(database_url or os.getenv("DATABASE_URL", "sqlite:///notifications.db"))
    Base.metadata.create_all(factory.kw["bind"])
    bus = bus or create_bus(os.getenv("BROKER_URL", "memory://"))

    def db():
        with factory() as session:
            yield session

    def on_event(event: dict) -> None:
        payload = event["payload"]
        key = event["type"] if event["type"] == "OrderCreated" else payload.get("status")
        template = TEXTS.get(key)
        if template is None:
            return
        with factory() as session:
            if session.scalar(select(Notification).where(Notification.event_id == event["event_id"])):
                return
            session.add(Notification(event_id=event["event_id"], passenger_id=payload["passenger_id"],
                                     order_id=payload["order_id"], text=template.format(**payload)))
            session.commit()
        logger.info("notification for passenger %s: %s", payload["passenger_id"], key)

    @app.get("/notifications", response_model=list[NotificationOut])
    def list_notifications(passenger_id: int | None = None, session: Session = Depends(db)):
        stmt = select(Notification).order_by(Notification.id.desc())
        if passenger_id:
            stmt = stmt.where(Notification.passenger_id == passenger_id)
        return session.scalars(stmt).all()

    bus.subscribe(SERVICE, on_event)
    app.state.bus = bus
    return app


app = create_app() if os.getenv("SERVICE_AUTOSTART", "1") == "1" else None
