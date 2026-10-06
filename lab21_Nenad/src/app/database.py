from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False},
                               poolclass=StaticPool if url in ("sqlite://", "sqlite:///:memory:") else None)

        @event.listens_for(engine, "connect")
        def _sqlite(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.create_function("lower", 1, lambda v: v.lower() if isinstance(v, str) else v)
        return engine
    return create_engine(url, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False)
