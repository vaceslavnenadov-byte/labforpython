"""Бизнес-логика железнодорожных перевозок."""

from collections import Counter

from decorators import log_call, timing
from exceptions import EntityNotFoundError, SeatUnavailableError, ValidationError
from models import Ticket, TicketStatus, Train, Wagon, WagonType


class RailwayService:
    def __init__(self) -> None:
        self.trains: list[Train] = []
        self.tickets: list[Ticket] = []
        self._next_id = {"train": 1, "wagon": 1, "ticket": 1}

    def _new_id(self, kind: str) -> int:
        new_id = self._next_id[kind]
        self._next_id[kind] += 1
        return new_id

    # ---------- Поезда ----------
    @log_call
    def add_train(self, number: str, route: str, departure: str, base_price: float,
                  wagon_types: list[WagonType]) -> Train:
        if not number.strip():
            raise ValidationError("Номер поезда не может быть пустым")
        if any(t.number == number for t in self.trains):
            raise ValidationError(f"Поезд {number} уже существует")
        if not wagon_types:
            raise ValidationError("Поезд должен содержать хотя бы один вагон")
        wagons = [Wagon(self._new_id("wagon"), i, wt) for i, wt in enumerate(wagon_types, start=1)]
        train = Train(self._new_id("train"), number, route, departure, base_price, wagons)
        self.trains.append(train)
        return train

    def get_train(self, train_id: int) -> Train:
        for train in self.trains:
            if train.id == train_id:
                return train
        raise EntityNotFoundError("Поезд", train_id)

    def find_trains(self, text: str) -> list[Train]:
        text = text.lower()
        return [t for t in self.trains if text in t.route.lower() or text in t.number.lower()]

    @log_call
    def delete_train(self, train_id: int) -> Train:
        train = self.get_train(train_id)
        if any(t.train_id == train_id and t.is_active() for t in self.tickets):
            raise ValidationError("Нельзя удалить поезд с активными билетами")
        self.trains.remove(train)
        return train

    # ---------- Билеты ----------
    def get_ticket(self, ticket_id: int) -> Ticket:
        for ticket in self.tickets:
            if ticket.id == ticket_id:
                return ticket
        raise EntityNotFoundError("Билет", ticket_id)

    def occupied_seats(self, train_id: int, wagon_number: int) -> set[int]:
        return {t.seat for t in self.tickets
                if t.train_id == train_id and t.wagon_number == wagon_number and t.is_active()}

    @log_call
    def book_ticket(self, train_id: int, wagon_number: int, seat: int, passenger: str) -> Ticket:
        train = self.get_train(train_id)
        wagon = train.find_wagon(wagon_number)
        if wagon is None:
            raise SeatUnavailableError(f"В поезде {train.number} нет вагона №{wagon_number}")
        if not 1 <= seat <= wagon.seats:
            raise SeatUnavailableError(f"В вагоне №{wagon_number} места с 1 по {wagon.seats}")
        if seat in self.occupied_seats(train_id, wagon_number):
            raise SeatUnavailableError(f"Место {seat} в вагоне №{wagon_number} уже занято")
        if not passenger.strip():
            raise ValidationError("Не указан пассажир")
        ticket = Ticket(self._new_id("ticket"), train_id, wagon_number, seat, passenger.strip(),
                        train.seat_price(wagon))
        self.tickets.append(ticket)
        return ticket

    @log_call
    def pay_ticket(self, ticket_id: int) -> Ticket:
        ticket = self.get_ticket(ticket_id)
        ticket.pay()
        return ticket

    @log_call
    def use_ticket(self, ticket_id: int) -> Ticket:
        ticket = self.get_ticket(ticket_id)
        ticket.use()
        return ticket

    @log_call
    def return_ticket(self, ticket_id: int) -> float:
        return self.get_ticket(ticket_id).refund()

    # ---------- Специализированные операции варианта 10 ----------
    @timing
    def train_load(self, train_id: int) -> float:
        """Загрузка поезда, %."""
        train = self.get_train(train_id)
        if train.capacity() == 0:
            raise ZeroDivisionError("У поезда нет мест")
        sold = sum(1 for t in self.tickets if t.train_id == train_id and t.is_active())
        return round(sold / train.capacity() * 100, 2)

    @timing
    def free_seats(self, train_id: int, wagon_type: WagonType | None = None) -> dict[int, list[int]]:
        """Свободные места: номер вагона -> список мест."""
        train = self.get_train(train_id)
        result = {}
        for wagon in train.wagons:
            if wagon_type and wagon.wagon_type != wagon_type:
                continue
            busy = self.occupied_seats(train_id, wagon.number)
            free = [s for s in range(1, wagon.seats + 1) if s not in busy]
            if free:
                result[wagon.number] = free
        return result

    @timing
    def statistics(self) -> dict[str, object]:
        statuses = Counter(t.status for t in self.tickets)
        prices = [t.price for t in self.tickets if t.status != TicketStatus.RETURNED]
        loads = {t.number: self.train_load.__wrapped__(self, t.id) for t in self.trains}
        return {
            "Поездов": len(self.trains),
            "Билетов всего": len(self.tickets),
            **{f"  {s.value}": statuses.get(s, 0) for s in TicketStatus},
            "Выручка (без возвратов)": round(sum(prices), 2),
            "Средняя цена билета": round(sum(prices) / len(prices), 2) if prices else 0,
            "Мин. цена": min(prices, default=0),
            "Макс. цена": max(prices, default=0),
            "Самый загруженный поезд": max(loads, key=loads.get) if loads else "-",
        }
