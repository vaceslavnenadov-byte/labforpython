"""Подключение к SQLite и инициализация схемы."""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
DEFAULT_DB = BASE_DIR / "railway.db"


def connect(path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    # isolation_level=None — автокоммит; транзакции открываются явно (BEGIN ... COMMIT/ROLLBACK)
    connection = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(connection: sqlite3.Connection, with_seed: bool = True) -> None:
    connection.executescript((BASE_DIR / "sql" / "schema.sql").read_text(encoding="utf-8"))
    if with_seed:
        connection.executescript((BASE_DIR / "sql" / "seed.sql").read_text(encoding="utf-8"))
    connection.commit()


def ensure_db(path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    """Создаёт БД с тестовыми данными при первом запуске."""
    is_new = not Path(path).exists()
    connection = connect(path)
    if is_new:
        init_db(connection)
    return connection
