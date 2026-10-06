from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {"pool_pre_ping": True}
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        # встроенная lower() в SQLite понимает только латиницу; заменяем её на Python-версию,
        # чтобы ILIKE работал с кириллицей так же, как в PostgreSQL
        @event.listens_for(engine, "connect")
        def _unicode_lower(connection, _):
            connection.create_function("lower", 1, lambda v: v.lower() if isinstance(v, str) else v)
    return engine


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    """Зависимость FastAPI: сессия на время одного запроса."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
