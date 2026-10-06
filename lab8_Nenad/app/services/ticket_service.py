"""Сервис продажи билетов. Не знает, где хранятся данные и каким тарифом считается цена."""

from datetime import date

from factories.ticket_factory import TicketFactory
from interfaces.repository import TicketRepository
from interfaces.strategies import PricingContext, PricingStrategy
from models.entities import DomainError, Ticket, Train
from models.enums import TicketStatus, WagonCategory


class TicketSalesService:
    def __init__(self, repository: TicketRepository, strategy: PricingStrategy,
                 trains: list[Train], today: date | None = None) -> None:
        self.repository = repository
        self.strategy = strategy
        self.trains = {t.number: t for t in trains}
        self.today = today or date.today()

    def set_strategy(self, strategy: PricingStrategy) -> None:
        self.strategy = strategy

    def get_train(self, number: str) -> Train:
        train = self.trains.get(number.upper())
        if train is None:
            raise DomainError(f"Поезд {number} не найден")
        return train

    def search_trains(self, city: str) -> list[Train]:
        return [t for t in self.trains.values() if city.lower() in t.route.lower()]

    def _active(self, train_number: str, category: WagonCategory) -> list[Ticket]:
        return [t for t in self.repository.get_all()
                if t.train_number == train_number and t.category == category
                and t.status == TicketStatus.SOLD]

    def occupancy(self, train: Train, category: WagonCategory) -> float:
        capacity = train.capacity.get(category, 0)
        if capacity == 0:
            return 1.0
        return len(self._active(train.number, category)) / capacity

    def quote(self, train_number: str, category: WagonCategory) -> float:
        train = self.get_train(train_number)
        context = PricingContext(self.occupancy(train, category), (train.departure - self.today).days)
        coefficient = TicketFactory.create(category, 0, train.number, "-", 0).coefficient
        return self.strategy.calculate(train.base_price, coefficient, context)

    def sell(self, train_number: str, category: WagonCategory | str, passenger: str) -> Ticket:
        if not passenger.strip():
            raise DomainError("Не указан пассажир")
        train = self.get_train(train_number)
        ticket = TicketFactory.create(category, self.repository.next_id(), train.number, passenger.strip(), 0)
        capacity = train.capacity.get(ticket.category, 0)
        busy = {t.seat for t in self._active(train.number, ticket.category)}
        free = [s for s in range(1, capacity + 1) if s not in busy]
        if not free:
            raise DomainError(f"В поезде {train.number} нет свободных мест категории «{ticket.title}»")
        ticket.price = self.quote(train.number, ticket.category)
        ticket.tariff = self.strategy.name
        ticket.seat = free[0]
        self.repository.add(ticket)
        return ticket

    def get_ticket(self, ticket_id: int) -> Ticket:
        ticket = self.repository.get(ticket_id)
        if ticket is None:
            raise DomainError(f"Билет #{ticket_id} не найден")
        return ticket

    def refund(self, ticket_id: int) -> float:
        ticket = self.get_ticket(ticket_id)
        if ticket.status == TicketStatus.REFUNDED:
            raise DomainError("Билет уже возвращён")
        ticket.status = TicketStatus.REFUNDED
        self.repository.update(ticket)
        return round(ticket.price * 0.9, 2)  # сбор за возврат 10%

    def restore(self, ticket_id: int) -> None:
        ticket = self.get_ticket(ticket_id)
        ticket.status = TicketStatus.SOLD
        self.repository.update(ticket)

    def remove(self, ticket_id: int) -> None:
        self.repository.delete(ticket_id)

    def statistics(self) -> dict[str, float]:
        sold = [t for t in self.repository.get_all() if t.status == TicketStatus.SOLD]
        return {
            "Продано": len(sold),
            "Возвращено": len(self.repository.get_all()) - len(sold),
            "Выручка": round(sum(t.price for t in sold), 2),
            "Средняя цена": round(sum(t.price for t in sold) / len(sold), 2) if sold else 0,
        }
