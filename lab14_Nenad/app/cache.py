"""Redis-кэш для GET /trains/{id}. Если REDIS_URL не задан или Redis недоступен — работает без кэша."""

import json
import logging

from app.config import settings

logger = logging.getLogger("cache")


class Cache:
    def __init__(self, client=None, ttl: int = 60) -> None:
        self.client = client
        self.ttl = ttl

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def get(self, key: str):
        if not self.enabled:
            return None
        try:
            raw = self.client.get(key)
            return json.loads(raw) if raw else None
        except Exception as error:   # Redis упал — продолжаем работу через БД
            logger.warning("Redis get failed: %s", error)
            return None

    def set(self, key: str, value) -> None:
        if self.enabled:
            try:
                self.client.set(key, json.dumps(value, default=str), ex=self.ttl)
            except Exception as error:
                logger.warning("Redis set failed: %s", error)

    def delete(self, key: str) -> None:
        if self.enabled:
            try:
                self.client.delete(key)
            except Exception as error:
                logger.warning("Redis delete failed: %s", error)


def create_cache() -> Cache:
    if not settings.redis_url:
        return Cache(None)
    try:
        import redis
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=1)
        client.ping()
        return Cache(client, settings.cache_ttl)
    except Exception as error:
        logger.warning("Redis unavailable: %s — cache disabled", error)
        return Cache(None)


cache = create_cache()


def get_cache() -> Cache:
    return cache
