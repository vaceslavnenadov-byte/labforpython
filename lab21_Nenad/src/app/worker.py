"""Фоновый worker.

1. relay_outbox — читает неопубликованные события из таблицы outbox и публикует их в брокер
   (с повторами). Если брокер недоступен, события остаются в outbox и будут отправлены позже —
   ни одно событие не теряется (Transactional Outbox).
2. handle_event — потребитель: создаёт уведомление пассажиру. Идемпотентен: повторная доставка
   того же event_id не создаёт дубликат (at-least-once доставка безопасна).

Запуск: python -m src.app.worker
"""

import logging
import signal
import threading

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.app.config import load_settings
from src.app.database import make_engine, make_session_factory
from src.app.events import create_broker, retrying
from src.app.models import Base, Notification
from src.app.repositories.repositories import NotificationRepository, OutboxRepository

logger = logging.getLogger("taxi.worker")

MESSAGES = {
    "order.assigned": "Заказ №{order_id}: назначен водитель {driver_name} ({car}). Стоимость {price} ₽",
    "order.in_progress": "Заказ №{order_id}: поездка началась ({route})",
    "order.completed": "Заказ №{order_id}: поездка завершена. К оплате {price} ₽",
    "order.cancelled": "Заказ №{order_id}: заказ отменён",
}


def relay_outbox(db: Session, broker, attempts: int = 3, delay: float = 0.2) -> int:
    published = 0
    for event in OutboxRepository(db).pending():
        message = {"event_id": event.event_id, "type": event.event_type, **event.payload}
        try:
            retrying(lambda message=message: broker.publish(message), attempts, delay)
        except Exception as error:
            logger.error("broker недоступен, событие %s останется в outbox: %s", event.event_id, error)
            break                       # порядок событий сохраняется
        event.published = True
        db.commit()
        published += 1
    return published


def handle_event(db: Session, event: dict) -> bool:
    notifications = NotificationRepository(db)
    if notifications.exists(event["event_id"]):
        logger.info("duplicate event %s skipped", event["event_id"])
        return False
    template = MESSAGES.get(event["type"], "Заказ №{order_id}: {status}")
    notifications.add(Notification(event_id=event["event_id"], user_id=event["passenger_id"],
                                   text=template.format_map(event)))
    try:
        db.commit()
    except IntegrityError:              # гонка двух потребителей
        db.rollback()
        return False
    logger.info("notification for user %s: %s", event["passenger_id"], event["type"])
    return True


def run(interval: float = 1.0) -> None:
    settings = load_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    sessions = make_session_factory(engine)
    broker = create_broker(settings.broker_url)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())

    def consume() -> None:
        while not stop.is_set():
            try:
                broker.consume("notifications", lambda e: _handle(sessions, e), stop.is_set)
            except Exception as error:
                logger.warning("consumer: %s; повтор через 3 с", error)
            stop.wait(3)

    threading.Thread(target=consume, daemon=True).start()
    logger.info("worker started (broker=%s)", settings.broker_url.split("@")[-1])
    while not stop.is_set():
        with sessions() as db:
            try:
                relay_outbox(db, broker)
            except Exception as error:
                logger.warning("relay: %s", error)
        stop.wait(interval)
    logger.info("worker stopped")


def _handle(sessions, event: dict) -> None:
    with sessions() as db:
        handle_event(db, event)


if __name__ == "__main__":
    run()
