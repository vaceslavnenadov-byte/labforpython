"""Настройки из переменных окружения (см. .env.example)."""

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./railway.db")
    redis_url: str | None = os.getenv("REDIS_URL")            # не задан — кэш выключен
    cache_ttl: int = int(os.getenv("CACHE_TTL", "60"))
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-in-production-please-use-32+-bytes")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    app_env: str = os.getenv("APP_ENV", "development")


settings = Settings()
