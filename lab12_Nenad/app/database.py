"""Подключение к БД. Адрес берётся из переменной окружения DATABASE_URL."""

import os

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

DEFAULT_URL = "postgresql+psycopg://taxi:taxi@localhost:5432/taxi"


def get_database_url() -> str:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    return os.getenv("DATABASE_URL", DEFAULT_URL)


def create_db_engine(url: str | None = None, echo: bool = False) -> Engine:
    url = url or get_database_url()
    engine = create_engine(url, echo=echo)
    if url.startswith("sqlite"):
        # в SQLite внешние ключи по умолчанию выключены
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_connection, _):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")
    return engine


def create_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False)
