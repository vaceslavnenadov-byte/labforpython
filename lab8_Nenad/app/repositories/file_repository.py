"""Хранение билетов в JSON-файле (доп. задание №1)."""

import json
from pathlib import Path

from factories.ticket_factory import TicketFactory
from models.entities import Ticket
from models.enums import TicketStatus, WagonCategory
from repositories.memory_repository import InMemoryTicketRepository


class FileTicketRepository(InMemoryTicketRepository):
    def __init__(self, path: str | Path) -> None:
        super().__init__()
        self.path = Path(path)
        if self.path.exists():
            for raw in json.loads(self.path.read_text(encoding="utf-8")):
                ticket = TicketFactory.create(
                    WagonCategory(raw["category"]), raw["id"], raw["train_number"],
                    raw["passenger"], raw["seat"])
                ticket.price, ticket.tariff = raw["price"], raw["tariff"]
                ticket.status = TicketStatus(raw["status"])
                super().add(ticket)

    def _save(self) -> None:
        data = [{
            "id": t.id, "category": t.category.value, "train_number": t.train_number,
            "passenger": t.passenger, "seat": t.seat, "price": t.price,
            "tariff": t.tariff, "status": t.status.value,
        } for t in self.get_all()]
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, ticket: Ticket) -> None:
        super().add(ticket)
        self._save()

    def update(self, ticket: Ticket) -> None:
        super().update(ticket)
        self._save()

    def delete(self, ticket_id: int) -> None:
        super().delete(ticket_id)
        self._save()
