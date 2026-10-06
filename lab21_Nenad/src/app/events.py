"""Брокер сообщений: RabbitMQ (amqp://), Redis Streams (redis://) или память (memory://, тесты)."""

import json
import logging
import time
from collections.abc import Callable

logger = logging.getLogger("taxi.events")
TOPIC = "taxi.orders"


class InMemoryBroker:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    def publish(self, event: dict) -> None:
        self.messages.append(event)

    def consume(self, group: str, handler: Callable[[dict], None], stop: Callable[[], bool]) -> None:
        while self.messages and not stop():
            handler(self.messages.pop(0))

    def ping(self) -> bool:
        return True


class RedisStreamBroker:
    def __init__(self, url: str) -> None:
        import redis
        self.redis = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=1)

    def publish(self, event: dict) -> None:
        self.redis.xadd(TOPIC, {"data": json.dumps(event, ensure_ascii=False)}, maxlen=10_000)

    def consume(self, group: str, handler: Callable[[dict], None], stop: Callable[[], bool]) -> None:
        try:
            self.redis.xgroup_create(TOPIC, group, id="0", mkstream=True)
        except Exception:
            pass
        while not stop():
            batches = self.redis.xreadgroup(group, "worker-1", {TOPIC: ">"}, count=20, block=1000)
            for _, messages in batches or []:
                for message_id, fields in messages:
                    handler(json.loads(fields["data"]))
                    self.redis.xack(TOPIC, group, message_id)

    def ping(self) -> bool:
        try:
            return bool(self.redis.ping())
        except Exception:
            return False


class RabbitBroker:
    def __init__(self, url: str) -> None:
        self.url = url

    def _channel(self):
        import pika
        connection = pika.BlockingConnection(pika.URLParameters(self.url))
        channel = connection.channel()
        channel.queue_declare(queue=TOPIC, durable=True)
        return connection, channel

    def publish(self, event: dict) -> None:
        import pika
        connection, channel = self._channel()
        try:
            channel.basic_publish("", TOPIC, json.dumps(event, ensure_ascii=False).encode(),
                                  pika.BasicProperties(delivery_mode=2))
        finally:
            connection.close()

    def consume(self, group: str, handler: Callable[[dict], None], stop: Callable[[], bool]) -> None:
        connection, channel = self._channel()
        try:
            for method, _, body in channel.consume(TOPIC, inactivity_timeout=1):
                if stop():
                    break
                if method is None:
                    continue
                handler(json.loads(body))
                channel.basic_ack(method.delivery_tag)
        finally:
            connection.close()

    def ping(self) -> bool:
        try:
            self._channel()[0].close()
            return True
        except Exception:
            return False


def create_broker(url: str):
    if url.startswith("amqp"):
        return RabbitBroker(url)
    if url.startswith("redis"):
        return RedisStreamBroker(url)
    return InMemoryBroker()


def retrying(func: Callable[[], None], attempts: int = 3, delay: float = 0.5) -> None:
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except Exception as error:
            if attempt == attempts:
                raise
            logger.warning("broker: попытка %d не удалась (%s)", attempt, error)
            time.sleep(delay * attempt)
