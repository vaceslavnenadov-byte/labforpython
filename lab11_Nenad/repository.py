"""Доступ к данным: только параметризованные SQL-запросы (защита от SQL injection)."""

import sqlite3

TRAIN_FIELDS = ("number", "name", "base_price", "status")
SORT_COLUMNS = {"number": "number", "price": "base_price", "name": "name"}


class TrainRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.db = connection

    def get_all(self, status: str | None = None, min_price: float | None = None,
                max_price: float | None = None, sort: str = "number", order: str = "asc") -> list[dict]:
        conditions, params = [], []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if min_price is not None:
            conditions.append("base_price >= ?")
            params.append(min_price)
        if max_price is not None:
            conditions.append("base_price <= ?")
            params.append(max_price)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        # имя столбца нельзя передать параметром — берём его только из белого списка
        column = SORT_COLUMNS[sort]
        direction = "DESC" if order == "desc" else "ASC"
        rows = self.db.execute(f"SELECT * FROM trains {where} ORDER BY {column} {direction}", params)
        return [dict(r) for r in rows]

    def get_by_id(self, train_id: int) -> dict | None:
        row = self.db.execute("SELECT * FROM trains WHERE id = ?", (train_id,)).fetchone()
        return dict(row) if row else None

    def create(self, data: dict) -> int:
        cursor = self.db.execute(
            "INSERT INTO trains (number, name, base_price, status) VALUES (?, ?, ?, ?)",
            (data["number"], data.get("name"), data["base_price"], data.get("status", "scheduled")))
        self.db.commit()
        return cursor.lastrowid

    def update(self, train_id: int, data: dict) -> None:
        columns = [f for f in TRAIN_FIELDS if f in data]
        assignments = ", ".join(f"{c} = ?" for c in columns)
        self.db.execute(f"UPDATE trains SET {assignments} WHERE id = ?",
                        [data[c] for c in columns] + [train_id])
        self.db.commit()

    def delete(self, train_id: int) -> None:
        self.db.execute("DELETE FROM trains WHERE id = ?", (train_id,))
        self.db.commit()

    def has_tickets(self, train_id: int) -> bool:
        row = self.db.execute(
            "SELECT EXISTS(SELECT 1 FROM tickets tk JOIN wagons w ON w.id = tk.wagon_id "
            "WHERE w.train_id = ? AND tk.status = 'paid')", (train_id,)).fetchone()
        return bool(row[0])

    def wagons(self, train_id: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT w.id, w.number, w.wagon_type, w.seats, "
            "       (SELECT COUNT(*) FROM tickets tk WHERE tk.wagon_id = w.id AND tk.status = 'paid') AS sold "
            "FROM wagons w WHERE w.train_id = ? ORDER BY w.number", (train_id,))
        return [dict(r) for r in rows]

    def schedule(self, train_id: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT rs.stop_order, s.name AS station, s.city, rs.arrival_time, rs.departure_time "
            "FROM route_stops rs JOIN stations s ON s.id = rs.station_id "
            "WHERE rs.train_id = ? ORDER BY rs.stop_order", (train_id,))
        return [dict(r) for r in rows]

    def busy_seats(self, wagon_id: int) -> set[int]:
        rows = self.db.execute("SELECT seat FROM tickets WHERE wagon_id = ? AND status = 'paid'", (wagon_id,))
        return {r[0] for r in rows}

    def search(self, from_city: str, to_city: str) -> list[dict]:
        rows = self.db.execute("""
            SELECT t.id, t.number, t.name, t.base_price, t.status,
                   sa.name AS from_station, a.departure_time,
                   sb.name AS to_station, b.arrival_time
            FROM trains t
            JOIN route_stops a ON a.train_id = t.id
            JOIN stations sa ON sa.id = a.station_id
            JOIN route_stops b ON b.train_id = t.id AND b.stop_order > a.stop_order
            JOIN stations sb ON sb.id = b.station_id
            WHERE sa.city LIKE ? AND sb.city LIKE ?
            ORDER BY a.departure_time""", (f"%{from_city}%", f"%{to_city}%"))
        return [dict(r) for r in rows]


class TicketRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.db = connection

    def get(self, ticket_id: int) -> dict | None:
        row = self.db.execute("""
            SELECT tk.*, p.full_name, p.passport, w.number AS wagon_number, w.train_id, t.number AS train_number
            FROM tickets tk
            JOIN passengers p ON p.id = tk.passenger_id
            JOIN wagons w ON w.id = tk.wagon_id
            JOIN trains t ON t.id = w.train_id
            WHERE tk.id = ?""", (ticket_id,)).fetchone()
        return dict(row) if row else None

    def find_passenger(self, passport: str) -> dict | None:
        row = self.db.execute("SELECT * FROM passengers WHERE passport = ?", (passport,)).fetchone()
        return dict(row) if row else None

    def insert_passenger(self, full_name: str, passport: str, email: str | None) -> int:
        return self.db.execute("INSERT INTO passengers (full_name, passport, email) VALUES (?, ?, ?)",
                               (full_name, passport, email)).lastrowid

    def insert_ticket(self, wagon_id: int, passenger_id: int, seat: int, price: float) -> int:
        return self.db.execute("INSERT INTO tickets (wagon_id, passenger_id, seat, price) VALUES (?, ?, ?, ?)",
                               (wagon_id, passenger_id, seat, price)).lastrowid

    def set_status(self, ticket_id: int, status: str) -> None:
        self.db.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
