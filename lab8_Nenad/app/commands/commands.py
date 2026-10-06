"""Command: операции кассы как объекты с историей и отменой."""

from interfaces.command import Command
from interfaces.strategies import PricingStrategy
from models.entities import Ticket
from models.enums import WagonCategory
from services.ticket_service import TicketSalesService


class SellTicketCommand:
    name = "SellTicket"

    def __init__(self, service: TicketSalesService, train: str, category: WagonCategory | str, passenger: str):
        self.service, self.train, self.category, self.passenger = service, train, category, passenger
        self.ticket: Ticket | None = None

    def execute(self) -> Ticket:
        self.ticket = self.service.sell(self.train, self.category, self.passenger)
        return self.ticket

    def undo(self) -> None:
        self.service.remove(self.ticket.id)


class RefundTicketCommand:
    name = "RefundTicket"

    def __init__(self, service: TicketSalesService, ticket_id: int):
        self.service, self.ticket_id = service, ticket_id

    def execute(self) -> float:
        return self.service.refund(self.ticket_id)

    def undo(self) -> None:
        self.service.restore(self.ticket_id)


class ChangeTariffCommand:
    name = "ChangeTariff"

    def __init__(self, service: TicketSalesService, strategy: PricingStrategy):
        self.service, self.strategy = service, strategy
        self.previous: PricingStrategy | None = None

    def execute(self) -> str:
        self.previous = self.service.strategy
        self.service.set_strategy(self.strategy)
        return self.strategy.name

    def undo(self) -> None:
        self.service.set_strategy(self.previous)


class CommandInvoker:
    """Выполняет команды и хранит историю для undo() (доп. задание №3)."""

    def __init__(self) -> None:
        self.history: list[Command] = []

    def execute(self, command: Command):
        result = command.execute()      # при исключении команда в историю не попадает
        self.history.append(command)
        return result

    def undo(self) -> str:
        if not self.history:
            raise IndexError("История команд пуста")
        command = self.history.pop()
        command.undo()
        return command.name

    def history_names(self) -> list[str]:
        return [c.name for c in self.history]
