from models.entities import Ticket


class InMemoryTicketRepository:
    def __init__(self) -> None:
        self._items: dict[int, Ticket] = {}

    def add(self, ticket: Ticket) -> None:
        self._items[ticket.id] = ticket

    def get(self, ticket_id: int) -> Ticket | None:
        return self._items.get(ticket_id)

    def get_all(self) -> list[Ticket]:
        return list(self._items.values())

    def update(self, ticket: Ticket) -> None:
        self._items[ticket.id] = ticket

    def delete(self, ticket_id: int) -> None:
        self._items.pop(ticket_id, None)

    def next_id(self) -> int:
        return max(self._items, default=0) + 1
