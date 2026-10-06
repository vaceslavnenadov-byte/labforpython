"""Redis-кэш (cache-aside). Если Redis недоступен — приложение работает напрямую с БД."""

import json
import logging

logger = logging.getLogger("taxi.cache")


class Cache:
    def __init__(self, client=None, ttl: int = 60) -> None:
        self.client = client
        self.ttl = ttl

    def get(self, key: str):
        if self.client is None:
            return None
        try:
            raw = self.client.get(key)
            return json.loads(raw) if raw else None
        except Exception as error:
            logger.warning("cache get failed: %s", error)
            return None

    def set(self, key: str, value) -> None:
        if self.client is not None:
            try:
                self.client.set(key, json.dumps(value, default=str), ex=self.ttl)
            except Exception as error:
                logger.warning("cache set failed: %s", error)

    def delete(self, key: str) -> None:
        if self.client is not None:
            try:
                self.client.delete(key)
            except Exception as error:
                logger.warning("cache delete failed: %s", error)

    def ping(self) -> bool:
        if self.client is None:
            return False
        try:
            return bool(self.client.ping())
        except Exception:
            return False


def create_cache(url: str | None, ttl: int) -> Cache:
    if not url:
        return Cache(None, ttl)
    import redis
    return Cache(redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=1), ttl)
