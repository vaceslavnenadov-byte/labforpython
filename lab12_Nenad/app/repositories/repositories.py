"""Repository-слой: все запросы к БД выполняются через SQLAlchemy ORM."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Car, CarClass, Client, Driver, DriverStatus, Trip, TripStatus


class BaseRepository:
    model = None

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, entity_id: int):
        return self.session.get(self.model, entity_id)

    def get_all(self, page: int = 1, page_size: int = 50) -> list:
        stmt = select(self.model).order_by(self.model.id).offset((page - 1) * page_size).limit(page_size)
        return list(self.session.scalars(stmt))

    def add(self, entity):
        self.session.add(entity)
        self.session.flush()          # получаем id до commit
        return entity

    def delete(self, entity) -> None:
        self.session.delete(entity)
        self.session.flush()

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(self.model))


class ClientRepository(BaseRepository):
    model = Client

    def search_by_name(self, text: str) -> list[Client]:
        stmt = select(Client).where(Client.full_name.ilike(f"%{text}%")).order_by(Client.full_name)
        return list(self.session.scalars(stmt))

    def get_by_phone(self, phone: str) -> Client | None:
        return self.session.scalar(select(Client).where(Client.phone == phone))


class DriverRepository(BaseRepository):
    model = Driver

    def find_free_driver(self, car_class: CarClass) -> tuple[Driver, Car] | None:
        """Свободный водитель с машиной нужного класса; лучшие по рейтингу — первыми."""
        stmt = (select(Driver, Car)
                .join(Driver.cars)
                .where(Driver.status == DriverStatus.FREE, Car.car_class == car_class)
                .order_by(Driver.rating.desc(), Driver.experience_years.desc())
                .limit(1))
        row = self.session.execute(stmt).first()
        return (row[0], row[1]) if row else None

    def sorted_by(self, field: str, descending: bool = True) -> list[Driver]:
        column = {"rating": Driver.rating, "experience": Driver.experience_years, "name": Driver.full_name}[field]
        stmt = select(Driver).order_by(column.desc() if descending else column.asc())
        return list(self.session.scalars(stmt))

    def with_cars(self) -> list[Driver]:
        """selectinload — машины всех водителей загружаются одним дополнительным запросом (нет N+1)."""
        return list(self.session.scalars(select(Driver).options(selectinload(Driver.cars)).order_by(Driver.id)))


class CarRepository(BaseRepository):
    model = Car

    def get_by_plate(self, plate: str) -> Car | None:
        return self.session.scalar(select(Car).where(Car.plate == plate))


class TripRepository(BaseRepository):
    model = Trip

    def by_client(self, client_id: int) -> list[Trip]:
        stmt = select(Trip).where(Trip.client_id == client_id).order_by(Trip.created_at.desc())
        return list(self.session.scalars(stmt))

    def filter(self, status: TripStatus | None = None, min_cost: float | None = None,
               car_class: CarClass | None = None, since: datetime | None = None,
               sort: str = "date", descending: bool = True) -> list[Trip]:
        conditions = []
        if status:
            conditions.append(Trip.status == status)
        if min_cost is not None:
            conditions.append(Trip.cost >= min_cost)
        if car_class:
            conditions.append(Trip.car_class == car_class)
        if since:
            conditions.append(Trip.created_at >= since)
        column = {"date": Trip.created_at, "cost": Trip.cost, "distance": Trip.distance_km}[sort]
        stmt = select(Trip).where(*conditions).order_by(column.desc() if descending else column.asc())
        return list(self.session.scalars(stmt))

    def statistics(self) -> dict:
        """Агрегирующий запрос COUNT/SUM/AVG/MIN/MAX по завершённым поездкам."""
        row = self.session.execute(
            select(func.count(Trip.id), func.sum(Trip.cost), func.avg(Trip.cost),
                   func.min(Trip.cost), func.max(Trip.cost), func.avg(Trip.distance_km))
            .where(Trip.status == TripStatus.COMPLETED)).one()
        by_class = self.session.execute(
            select(Trip.car_class, func.count(Trip.id), func.sum(Trip.cost))
            .where(Trip.status == TripStatus.COMPLETED).group_by(Trip.car_class)).all()
        return {
            "count": row[0], "revenue": round(row[1] or 0, 2), "avg_cost": round(row[2] or 0, 2),
            "min_cost": row[3] or 0, "max_cost": row[4] or 0, "avg_distance": round(row[5] or 0, 2),
            "by_class": {cls.value: {"trips": n, "revenue": round(s, 2)} for cls, n, s in by_class},
        }
