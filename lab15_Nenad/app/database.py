from flask import current_app, g
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def init_engine(url: str):
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False},
                               poolclass=StaticPool if url == "sqlite://" else None)

        @event.listens_for(engine, "connect")
        def _sqlite_setup(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.create_function("lower", 1, lambda v: v.lower() if isinstance(v, str) else v)
        return engine
    return create_engine(url, pool_pre_ping=True)


def get_session() -> Session:
    """Одна сессия на HTTP-запрос (хранится в g), закрывается в teardown."""
    if "db" not in g:
        g.db = current_app.extensions["session_factory"]()
    return g.db


def close_session(exception=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        if exception is not None:
            db.rollback()
        db.close()


def make_session_factory(engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False)
