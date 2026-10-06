"""Хранение билетов в JSON-файле. Взаимозаменяемо с InMemoryTicketRepository (LSP)."""

import json
from dataclasses import asdict
from pathlib import Path

from models.entities import Tariff, Ticket
from models.enums import TicketStatus
from repositories.memory_repository import InMemoryTicketRepository


class JsonTicketRepository(InMemoryTicketRepository):
    def __init__(self, path: str | Path) -> None:
        super().__init__()
        self.path = Path(path)
        if self.path.exists():
            for raw in json.loads(self.path.read_text(encoding="utf-8")):
                raw["tariff"] = Tariff(**raw["tariff"])
                raw["status"] = TicketStatus(raw["status"])
                super().add(Ticket(**raw))

    def _flush(self) -> None:
        data = []
        for ticket in self.get_all():
            item = asdict(ticket)
            item["status"] = ticket.status.value
            data.append(item)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, ticket: Ticket) -> None:
        super().add(ticket)
        self._flush()

    def update(self, ticket: Ticket) -> None:
        super().update(ticket)
        self._flush()
