"""Асинхронное взаимодействие через брокер сообщений.

BROKER_URL=amqp://...   → RabbitMQ (fanout exchange, своя очередь у каждого сервиса-подписчика)
BROKER_URL=redis://...  → Redis Streams (consumer group на каждый сервис)
BROKER_URL=memory://    → в памяти процесса (тесты)
"""

import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Callable

logger = logging.getLogger("events")
Handler = Callable[[dict], None]
EXCHANGE = "taxi.events"


def make_event(event_type: str, payload: dict, source: str) -> dict:
    return {"event_id": uuid.uuid4().hex, "type": event_type, "source": source,
            "occurred_at": datetime.now(timezone.utc).isoformat(), "payload": payload}


class InMemoryBus:
    def __init__(self) -> None:
        self.handlers: list[Handler] = []
        self.published: list[dict] = []

    def publish(self, event: dict) -> None:
        self.published.append(event)
        for handler in list(self.handlers):
            handler(event)

    def subscribe(self, group: str, handler: Handler) -> None:
        self.handlers.append(handler)

    def close(self) -> None:
        pass


class RedisStreamBus:
    def __init__(self, url: str) -> None:
        import redis
        self.redis = redis.Redis.from_url(url, decode_responses=True)
        self._stop = threading.Event()

    def publish(self, event: dict) -> None:
        self.redis.xadd(EXCHANGE, {"data": json.dumps(event, ensure_ascii=False)}, maxlen=10_000)

    def subscribe(self, group: str, handler: Handler) -> None:
        try:
            self.redis.xgroup_create(EXCHANGE, group, id="$", mkstream=True)
        except Exception:
            pass  # группа уже существует

        def loop() -> None:
            consumer = f"{group}-{uuid.uuid4().hex[:6]}"
            while not self._stop.is_set():
                try:
                    batches = self.redis.xreadgroup(group, consumer, {EXCHANGE: ">"}, count=10, block=1000)
                except Exception as error:
                    logger.warning("broker read failed: %s", error)
                    time.sleep(1)
                    continue
                for _, messages in batches or []:
                    for message_id, fields in messages:
                        try:
                            handler(json.loads(fields["data"]))
                            self.redis.xack(EXCHANGE, group, message_id)
                        except Exception:
                            logger.exception("event handling failed")

        threading.Thread(target=loop, daemon=True, name=f"consumer-{group}").start()

    def close(self) -> None:
        self._stop.set()


class RabbitMQBus:
    def __init__(self, url: str) -> None:
        self.url = url
        self._lock = threading.Lock()
        self._publish_channel = None

    def _connect(self):
        import pika
        connection = pika.BlockingConnection(pika.URLParameters(self.url))
        channel = connection.channel()
        channel.exchange_declare(exchange=EXCHANGE, exchange_type="fanout", durable=True)
        return connection, channel

    def publish(self, event: dict) -> None:
        import pika
        with self._lock:
            if self._publish_channel is None or self._publish_channel.is_closed:
                _, self._publish_channel = self._connect()
            self._publish_channel.basic_publish(
                exchange=EXCHANGE, routing_key="", body=json.dumps(event, ensure_ascii=False),
                properties=pika.BasicProperties(delivery_mode=2, content_type="application/json"))

    def subscribe(self, group: str, handler: Handler) -> None:
        def loop() -> None:
            while True:
                try:
                    _, channel = self._connect()
                    channel.queue_declare(queue=group, durable=True)
                    channel.queue_bind(queue=group, exchange=EXCHANGE)

                    def on_message(ch, method, properties, body):
                        try:
                            handler(json.loads(body))
                        finally:
                            ch.basic_ack(delivery_tag=method.delivery_tag)

                    channel.basic_consume(queue=group, on_message_callback=on_message)
                    channel.start_consuming()
                except Exception as error:
                    logger.warning("RabbitMQ consumer reconnect: %s", error)
                    time.sleep(2)

        threading.Thread(target=loop, daemon=True, name=f"consumer-{group}").start()

    def close(self) -> None:
        pass


def create_bus(url: str):
    if url.startswith("amqp"):
        return RabbitMQBus(url)
    if url.startswith("redis"):
        return RedisStreamBus(url)
    return InMemoryBus()
