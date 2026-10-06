"""Репозитории: асинхронные запросы к БД."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from database.models import Station, Ticket, TicketStatus, Train, User, WagonType


class TrainRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, train_id: int) -> Train | None:
        return await self.session.get(Train, train_id)

    async def search(self, from_city: str, to_city: str, after: datetime) -> list[Train]:
        src, dst = aliased(Station), aliased(Station)
        stmt = (select(Train).join(src, Train.from_station_id == src.id).join(dst, Train.to_station_id == dst.id)
                .where(src.city.ilike(from_city), dst.city.ilike(to_city), Train.departure >= after)
                .order_by(Train.departure))
        return list((await self.session.scalars(stmt)).unique())

    async def schedule(self, after: datetime, limit: int = 8) -> list[Train]:
        stmt = select(Train).where(Train.departure >= after).order_by(Train.departure).limit(limit)
        return list((await self.session.scalars(stmt)).unique())

    async def cities(self) -> list[str]:
        return list(await self.session.scalars(select(Station.city).distinct().order_by(Station.city)))

    async def busy_seats(self, train_id: int, wagon_type: WagonType) -> set[int]:
        stmt = select(Ticket.seat).where(Ticket.train_id == train_id, Ticket.wagon_type == wagon_type,
                                         Ticket.status == TicketStatus.ACTIVE)
        return set(await self.session.scalars(stmt))


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.session.scalar(select(User).where(User.telegram_id == telegram_id))

    async def add(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user

    async def all(self) -> list[User]:
        return list(await self.session.scalars(select(User).order_by(User.registered_at)))


class TicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, ticket_id: int) -> Ticket | None:
        # populate_existing: заново загрузить объект вместе со связями (поезд, станции) — в async-режиме
        # «ленивая» подгрузка связей при обращении к атрибуту невозможна
        return await self.session.get(Ticket, ticket_id, populate_existing=True)

    async def by_user(self, user_id: int) -> list[Ticket]:
        stmt = select(Ticket).where(Ticket.user_id == user_id).order_by(Ticket.created_at.desc())
        return list((await self.session.scalars(stmt)).unique())

    async def add(self, ticket: Ticket) -> Ticket:
        self.session.add(ticket)
        await self.session.flush()
        return ticket

    async def counts(self) -> dict:
        active = await self.session.scalar(select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.ACTIVE))
        revenue = await self.session.scalar(select(func.coalesce(func.sum(Ticket.price), 0))
                                            .where(Ticket.status == TicketStatus.ACTIVE))
        return {"active": active, "revenue": round(revenue, 2),
                "all": await self.session.scalar(select(func.count(Ticket.id)))}
