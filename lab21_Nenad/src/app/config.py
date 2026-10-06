"""Настройки приложения — только из переменных окружения."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./taxi.db"
    redis_url: str | None = None
    broker_url: str = "memory://"
    jwt_secret: str = "dev-secret-change-me-please-32-bytes!"
    jwt_expire_minutes: int = 60
    cache_ttl: int = 60
    app_env: str = "development"
    log_level: str = "INFO"
    admin_email: str | None = None
    admin_password: str | None = None


def load_settings() -> Settings:
    env = os.getenv
    return Settings(
        database_url=env("DATABASE_URL", Settings.database_url),
        redis_url=env("REDIS_URL") or None,
        broker_url=env("BROKER_URL", Settings.broker_url),
        jwt_secret=env("JWT_SECRET", Settings.jwt_secret),
        jwt_expire_minutes=int(env("JWT_EXPIRE_MINUTES", "60")),
        cache_ttl=int(env("CACHE_TTL", "60")),
        app_env=env("APP_ENV", "development"),
        log_level=env("LOG_LEVEL", "INFO"),
        admin_email=env("ADMIN_EMAIL") or None,
        admin_password=env("ADMIN_PASSWORD") or None,
    )
