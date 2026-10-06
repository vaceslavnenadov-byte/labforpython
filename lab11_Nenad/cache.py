"""Redis-кэш. Если Redis недоступен, приложение продолжает работать без кэша."""

import json
import logging
import os

logger = logging.getLogger("cache")


class RedisCache:
    def __init__(self, client) -> None:
        self.client = client

    def get_json(self, key: str):
        raw = self.client.get(key)
        return json.loads(raw) if raw is not None else None

    def set_json(self, key: str, value, ttl: int) -> None:
        self.client.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)

    def delete(self, *keys: str) -> None:
        if keys:
            self.client.delete(*keys)

    def ttl(self, key: str) -> int:
        return self.client.ttl(key)

    def incr_view(self, train_number: str) -> None:
        self.client.zincrby("trains:popular", 1, train_number)

    def popular(self, limit: int = 5) -> list[tuple[str, int]]:
        return [(name, int(score)) for name, score in
                self.client.zrevrange("trains:popular", 0, limit - 1, withscores=True)]

    def push_search(self, query: str) -> None:
        self.client.lpush("search:history", query)
        self.client.ltrim("search:history", 0, 9)      # храним 10 последних запросов
        self.client.expire("search:history", 3600)

    def search_history(self) -> list[str]:
        return self.client.lrange("search:history", 0, -1)

    def count_request(self) -> int:
        return self.client.incr("stats:requests")


class NullCache(RedisCache):
    """Заглушка на случай недоступности Redis."""

    def __init__(self) -> None:
        super().__init__(None)

    def get_json(self, key):
        return None

    def set_json(self, key, value, ttl):
        pass

    def delete(self, *keys):
        pass

    def ttl(self, key):
        return -2

    def incr_view(self, train_number):
        pass

    def popular(self, limit=5):
        return []

    def push_search(self, query):
        pass

    def search_history(self):
        return []

    def count_request(self):
        return 0


def create_cache(url: str | None = None) -> RedisCache:
    url = url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis
        client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=1)
        client.ping()
        logger.info("Redis connected: %s", url)
        return RedisCache(client)
    except Exception as error:  # нет библиотеки или сервера
        logger.warning("Redis unavailable (%s) — cache disabled", error)
        return NullCache()
