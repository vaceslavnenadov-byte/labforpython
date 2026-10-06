"""Хранение рейсов и билетов в SQLite."""

import sqlite3
from datetime import datetime

from src.models.entities import Route, Ticket, TicketStatus

SCHEMA = """
CREATE TABLE IF NOT EXISTS routes (
    id INTEGER PRIMARY KEY,
    train_number TEXT NOT NULL,
    from_city TEXT NOT NULL,
    to_city TEXT NOT NULL,
    departure TEXT NOT NULL,
    seats INTEGER NOT NULL CHECK (seats > 0),
    price REAL NOT NULL CHECK (price > 0),
    UNIQUE (train_number, departure)
);
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY,
    route_id INTEGER NOT NULL REFERENCES routes(id),
    passenger TEXT NOT NULL,
    seat INTEGER NOT NULL,
    price REAL NOT NULL,
    status TEXT NOT NULL,
    sold_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_active_seat ON tickets(route_id, seat) WHERE status = 'sold';
"""


def connect(path: str = ":memory:") -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    # встроенная lower() SQLite работает только с латиницей — ошибка найдена интеграционным тестом поиска
    connection.create_function("lower", 1, lambda value: value.lower() if isinstance(value, str) else value)
    connection.executescript(SCHEMA)
    return connection


class RouteRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.db = connection

    @staticmethod
    def _to_route(row) -> Route:
        return Route(row["id"], row["train_number"], row["from_city"], row["to_city"],
                     datetime.fromisoformat(row["departure"]), row["seats"], row["price"])

    def add(self, route: Route) -> Route:
        cursor = self.db.execute(
            "INSERT INTO routes (train_number, from_city, to_city, departure, seats, price) VALUES (?, ?, ?, ?, ?, ?)",
            (route.train_number, route.from_city, route.to_city, route.departure.isoformat(), route.seats, route.price))
        self.db.commit()
        route.id = cursor.lastrowid
        return route

    def find_by_id(self, route_id: int) -> Route | None:
        row = self.db.execute("SELECT * FROM routes WHERE id = ?", (route_id,)).fetchone()
        return self._to_route(row) if row else None

    def exists(self, train_number: str, departure: datetime) -> bool:
        row = self.db.execute("SELECT 1 FROM routes WHERE train_number = ? AND departure = ?",
                              (train_number, departure.isoformat())).fetchone()
        return row is not None

    def search(self, from_city: str, to_city: str, day: str | None = None) -> list[Route]:
        sql = "SELECT * FROM routes WHERE lower(from_city) = lower(?) AND lower(to_city) = lower(?)"
        params: list = [from_city, to_city]
        if day:
            sql += " AND substr(departure, 1, 10) = ?"
            params.append(day)
        return [self._to_route(r) for r in self.db.execute(sql + " ORDER BY departure", params)]

    def find_all(self) -> list[Route]:
        return [self._to_route(r) for r in self.db.execute("SELECT * FROM routes ORDER BY departure")]


class TicketRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.db = connection

    @staticmethod
    def _to_ticket(row) -> Ticket:
        return Ticket(row["id"], row["route_id"], row["passenger"], row["seat"], row["price"],
                      TicketStatus(row["status"]), datetime.fromisoformat(row["sold_at"]) if row["sold_at"] else None)

    def add(self, ticket: Ticket) -> Ticket:
        cursor = self.db.execute(
            "INSERT INTO tickets (route_id, passenger, seat, price, status, sold_at) VALUES (?, ?, ?, ?, ?, ?)",
            (ticket.route_id, ticket.passenger, ticket.seat, ticket.price, ticket.status.value,
             ticket.sold_at.isoformat() if ticket.sold_at else None))
        self.db.commit()
        ticket.id = cursor.lastrowid
        return ticket

    def find_by_id(self, ticket_id: int) -> Ticket | None:
        row = self.db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return self._to_ticket(row) if row else None

    def update_status(self, ticket_id: int, status: TicketStatus) -> None:
        self.db.execute("UPDATE tickets SET status = ? WHERE id = ?", (status.value, ticket_id))
        self.db.commit()

    def taken_seats(self, route_id: int) -> set[int]:
        rows = self.db.execute("SELECT seat FROM tickets WHERE route_id = ? AND status = 'sold'", (route_id,))
        return {r["seat"] for r in rows}

    def find_by_passenger(self, passenger: str) -> list[Ticket]:
        rows = self.db.execute("SELECT * FROM tickets WHERE passenger = ? ORDER BY id", (passenger,))
        return [self._to_ticket(r) for r in rows]
