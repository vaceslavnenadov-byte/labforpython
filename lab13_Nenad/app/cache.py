"""RedisCache — работа с Redis: String, Hash, List, Sorted Set, Set, счётчики, Pub/Sub, блокировки."""

import json
from datetime import datetime

CHANNEL = "trains.events"


def _default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(type(value))


class RedisCache:
    def __init__(self, client, ttl: int = 300) -> None:
        self.r = client
        self.ttl = ttl

    # String + TTL: кэш документа поезда
    def get_train(self, train_id: int) -> dict | None:
        raw = self.r.get(f"train:{train_id}")
        if raw is None:
            self.r.incr("stats:cache_miss")
            return None
        self.r.incr("stats:cache_hit")
        return json.loads(raw)

    def set_train(self, doc: dict) -> None:
        self.r.set(f"train:{doc['_id']}", json.dumps(doc, default=_default, ensure_ascii=False), ex=self.ttl)

    def invalidate(self, train_id: int) -> None:
        self.r.delete(f"train:{train_id}", f"train:{train_id}:seats")

    def ttl_of(self, train_id: int) -> int:
        return self.r.ttl(f"train:{train_id}")

    # Hash: доступные места по вагонам
    def set_seats(self, train_id: int, seats: dict[int, int]) -> None:
        key = f"train:{train_id}:seats"
        self.r.delete(key)
        if seats:
            self.r.hset(key, mapping={str(k): v for k, v in seats.items()})
            self.r.expire(key, self.ttl)

    def get_seats(self, train_id: int) -> dict[int, int] | None:
        data = self.r.hgetall(f"train:{train_id}:seats")
        return {int(k): int(v) for k, v in data.items()} if data else None

    # Sorted Set: ближайшие отправления (score — время отправления)
    def add_departure(self, train_id: int, number: str, when: datetime) -> None:
        self.r.zadd("departures", {f"{train_id}:{number}": when.timestamp()})

    def remove_departure(self, train_id: int, number: str) -> None:
        self.r.zrem("departures", f"{train_id}:{number}")

    def nearest_departures(self, after: datetime, limit: int = 5) -> list[tuple[str, datetime]]:
        items = self.r.zrangebyscore("departures", after.timestamp(), "+inf", start=0, num=limit, withscores=True)
        return [(member.split(":", 1)[1], datetime.fromtimestamp(score)) for member, score in items]

    # List: последние поисковые запросы
    def push_search(self, query: str) -> None:
        self.r.lpush("search:recent", query)
        self.r.ltrim("search:recent", 0, 9)

    def recent_searches(self) -> list[str]:
        return self.r.lrange("search:recent", 0, -1)

    # Set: множество поездов, по которым идёт продажа
    def mark_active(self, number: str, active: bool) -> None:
        (self.r.sadd if active else self.r.srem)("trains:active", number)

    def active_trains(self) -> set[str]:
        return self.r.smembers("trains:active")

    # Счётчики, очистка, статус
    def stats(self) -> dict:
        return {"hits": int(self.r.get("stats:cache_hit") or 0), "misses": int(self.r.get("stats:cache_miss") or 0),
                "keys": sorted(self.r.keys("*"))}

    def clear(self) -> int:
        keys = self.r.keys("train:*")
        return self.r.delete(*keys) if keys else 0

    # Pub/Sub: события изменения объектов
    def publish(self, event: str, train_id: int) -> None:
        self.r.publish(CHANNEL, json.dumps({"event": event, "train_id": train_id}))

    # Защита от cache stampede: только один процесс загружает объект из MongoDB
    def acquire_lock(self, train_id: int, seconds: int = 5) -> bool:
        return bool(self.r.set(f"lock:train:{train_id}", "1", nx=True, ex=seconds))

    def release_lock(self, train_id: int) -> None:
        self.r.delete(f"lock:train:{train_id}")
