"""Хранение в памяти."""

from models.entities import Ticket, Trip


class InMemoryTripRepository:
    def __init__(self) -> None:
        self._trips: dict[int, Trip] = {}

    def add(self, trip: Trip) -> None:
        self._trips[trip.id] = trip

    def get(self, trip_id: int) -> Trip | None:
        return self._trips.get(trip_id)

    def get_all(self) -> list[Trip]:
        return list(self._trips.values())


class InMemoryTicketRepository:
    def __init__(self) -> None:
        self._tickets: dict[int, Ticket] = {}

    def add(self, ticket: Ticket) -> None:
        self._tickets[ticket.id] = ticket

    def update(self, ticket: Ticket) -> None:
        self._tickets[ticket.id] = ticket

    def get(self, ticket_id: int) -> Ticket | None:
        return self._tickets.get(ticket_id)

    def get_all(self) -> list[Ticket]:
        return list(self._tickets.values())

    def find_by_trip(self, trip_id: int) -> list[Ticket]:
        return [t for t in self._tickets.values() if t.trip_id == trip_id]

    def next_id(self) -> int:
        return max(self._tickets, default=0) + 1
