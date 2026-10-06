"""Конфигурация только из переменных окружения — секретов в коде нет."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    redis_url: str | None
    cache_ttl: int
    log_level: str
    app_env: str


def load_settings() -> Settings:
    if os.getenv("DATABASE_URL"):
        database_url = os.environ["DATABASE_URL"]
    elif os.getenv("DATABASE_HOST"):
        database_url = ("postgresql+psycopg://{user}:{password}@{host}:{port}/{name}".format(
            user=os.getenv("DATABASE_USER", "taxi"), password=os.getenv("DATABASE_PASSWORD", ""),
            host=os.environ["DATABASE_HOST"], port=os.getenv("DATABASE_PORT", "5432"),
            name=os.getenv("DATABASE_NAME", "taxi")))
    else:
        database_url = "sqlite:///./taxi.db"
    return Settings(
        database_url=database_url,
        redis_url=os.getenv("REDIS_URL") or None,
        cache_ttl=int(os.getenv("CACHE_TTL", "60")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        app_env=os.getenv("APP_ENV", "development"),
    )
