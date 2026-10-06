"""Небольшие специализированные интерфейсы хранилищ (ISP)."""

from typing import Protocol

from models.entities import Ticket, Trip


class TripReader(Protocol):
    def get(self, trip_id: int) -> Trip | None: ...
    def get_all(self) -> list[Trip]: ...


class TripWriter(Protocol):
    def add(self, trip: Trip) -> None: ...


class TicketReader(Protocol):
    def get(self, ticket_id: int) -> Ticket | None: ...
    def get_all(self) -> list[Ticket]: ...
    def find_by_trip(self, trip_id: int) -> list[Ticket]: ...


class TicketWriter(Protocol):
    def add(self, ticket: Ticket) -> None: ...
    def update(self, ticket: Ticket) -> None: ...
    def next_id(self) -> int: ...


class TicketRepository(TicketReader, TicketWriter, Protocol):
    """Полный доступ к билетам нужен только сервису бронирования."""
