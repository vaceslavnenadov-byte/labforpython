"""Бизнес-логика бота: поиск поездов, бронирование, просмотр, изменение и возврат билетов."""

from collections import Counter
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Station, Ticket, TicketStatus, Train, User, WagonType
from database.repository import TicketRepository, TrainRepository, UserRepository


class BookingError(Exception):
    """Нарушение бизнес-правила (место занято, билет чужой и т. п.)."""


class RailwayService:
    def __init__(self, session: AsyncSession, admin_ids: frozenset[int] = frozenset()) -> None:
        self.session = session
        self.trains = TrainRepository(session)
        self.users = UserRepository(session)
        self.tickets = TicketRepository(session)
        self.admin_ids = admin_ids

    # ---------- пользователи ----------
    async def register_user(self, telegram_id: int, full_name: str, username: str | None) -> User:
        user = await self.users.get_by_telegram_id(telegram_id)
        if user is None:
            user = await self.users.add(User(telegram_id=telegram_id, full_name=full_name, username=username,
                                             is_admin=telegram_id in self.admin_ids))
        user.messages_count += 1
        await self.session.commit()
        return user

    # ---------- поиск ----------
    async def schedule(self, now: datetime | None = None) -> list[Train]:
        return await self.trains.schedule(now or datetime.now())

    async def search(self, from_city: str, to_city: str, now: datetime | None = None) -> list[Train]:
        return await self.trains.search(from_city, to_city, now or datetime.now())

    async def cities(self) -> list[str]:
        return await self.trains.cities()

    async def get_train(self, train_id: int) -> Train:
        train = await self.trains.get(train_id)
        if train is None:
            raise BookingError("Поезд не найден.")
        return train

    async def available_types(self, train_id: int) -> list[tuple[WagonType, int, float]]:
        """(тип вагона, свободно мест, цена) — только типы, где есть свободные места."""
        train = await self.get_train(train_id)
        result = []
        for wagon_type in WagonType:
            capacity = train.capacity(wagon_type)
            if capacity:
                free = capacity - len(await self.trains.busy_seats(train_id, wagon_type))
                if free > 0:
                    result.append((wagon_type, free, train.price(wagon_type)))
        return result

    async def free_seats(self, train_id: int, wagon_type: WagonType) -> list[int]:
        train = await self.get_train(train_id)
        busy = await self.trains.busy_seats(train_id, wagon_type)
        return [s for s in range(1, train.capacity(wagon_type) + 1) if s not in busy]

    # ---------- CRUD билетов ----------
    async def book(self, user: User, train_id: int, wagon_type: WagonType, seat: int, passenger_name: str) -> Ticket:
        train = await self.get_train(train_id)
        if train.departure <= datetime.now():
            raise BookingError("Поезд уже отправился.")
        if seat not in await self.free_seats(train_id, wagon_type):
            raise BookingError(f"Место {seat} уже занято или не существует.")
        ticket = Ticket(user_id=user.id, train_id=train_id, wagon_type=wagon_type, seat=seat,
                        passenger_name=passenger_name, price=train.price(wagon_type))
        try:
            await self.tickets.add(ticket)
            await self.session.commit()
        except IntegrityError:                       # гонка: место заняли параллельно
            await self.session.rollback()
            raise BookingError(f"Место {seat} только что заняли, выберите другое.") from None
        return await self.tickets.get(ticket.id)

    async def user_tickets(self, user: User) -> list[Ticket]:
        return await self.tickets.by_user(user.id)

    async def get_own_ticket(self, user: User, ticket_id: int) -> Ticket:
        ticket = await self.tickets.get(ticket_id)
        if ticket is None or (ticket.user_id != user.id and not user.is_admin):
            raise BookingError("Билет не найден.")
        return ticket

    async def rename_passenger(self, user: User, ticket_id: int, new_name: str) -> Ticket:
        ticket = await self.get_own_ticket(user, ticket_id)
        if ticket.status != TicketStatus.ACTIVE:
            raise BookingError("Возвращённый билет изменить нельзя.")
        ticket.passenger_name = new_name
        await self.session.commit()
        return ticket

    async def return_ticket(self, user: User, ticket_id: int) -> float:
        ticket = await self.get_own_ticket(user, ticket_id)
        if ticket.status == TicketStatus.RETURNED:
            raise BookingError("Билет уже возвращён.")
        ticket.status = TicketStatus.RETURNED
        await self.session.commit()
        return round(ticket.price * 0.9, 2)

    # ---------- администрирование ----------
    async def statistics(self, popular_commands: Counter | None = None) -> dict:
        stats = await self.tickets.counts()
        stats["users"] = len(await self.users.all())
        stats["messages"] = await self.session.scalar(select(func.coalesce(func.sum(User.messages_count), 0)))
        stats["trains"] = await self.session.scalar(select(func.count(Train.id)))
        stats["stations"] = await self.session.scalar(select(func.count(Station.id)))
        if popular_commands:
            stats["popular"] = popular_commands.most_common(1)[0][0]
        return stats
