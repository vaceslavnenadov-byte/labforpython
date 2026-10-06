"""Подключение к Redis. Без сервера — fakeredis (флаг --mock)."""

import os


def get_redis(use_mock: bool = False):
    if use_mock:
        import fakeredis
        return fakeredis.FakeRedis(decode_responses=True)
    import redis
    client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                                  decode_responses=True, socket_connect_timeout=2)
    client.ping()
    return client
