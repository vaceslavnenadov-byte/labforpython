"""Redis-кэш (Cache-Aside). Недоступный Redis не ломает приложение — запросы идут в БД."""

import json
import logging

logger = logging.getLogger("taxi.cache")


class Cache:
    def __init__(self, client=None, ttl: int = 60) -> None:
        self.client = client
        self.ttl = ttl
        self.hits = 0
        self.misses = 0

    def get(self, key: str):
        if self.client is None:
            return None
        try:
            raw = self.client.get(key)
        except Exception as error:
            logger.warning("Redis недоступен (get %s): %s", key, error)
            return None
        if raw is None:
            self.misses += 1
            return None
        self.hits += 1
        return json.loads(raw)

    def set(self, key: str, value, ttl: int | None = None) -> None:
        if self.client is None:
            return
        try:
            self.client.set(key, json.dumps(value, default=str, ensure_ascii=False), ex=ttl or self.ttl)
        except Exception as error:
            logger.warning("Redis недоступен (set %s): %s", key, error)

    def delete(self, *keys: str) -> None:
        if self.client is None or not keys:
            return
        try:
            self.client.delete(*keys)
        except Exception as error:
            logger.warning("Redis недоступен (delete): %s", error)

    def ping(self) -> bool:
        try:
            return self.client is not None and bool(self.client.ping())
        except Exception:
            return False


def create_cache(url: str | None, ttl: int) -> Cache:
    if not url:
        return Cache(None, ttl)
    import redis
    return Cache(redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1), ttl)
