"""Асинхронное подключение к БД (SQLAlchemy + aiosqlite / asyncpg)."""

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from database.models import Base


def create_engine(url: str) -> AsyncEngine:
    return create_async_engine(url)


async def init_models(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)
