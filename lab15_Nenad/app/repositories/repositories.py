from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.models import CarClass, Client, Driver, Trip, TripStatus

TRIP_SORTS = {"date": Trip.created_at, "cost": Trip.cost, "distance": Trip.distance_km}


class DriverRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def all(self) -> list[Driver]:
        return list(self.db.scalars(select(Driver).order_by(Driver.full_name)))

    def get(self, driver_id: int) -> Driver | None:
        return self.db.get(Driver, driver_id)

    def add(self, driver: Driver) -> Driver:
        self.db.add(driver)        # INSERT выполнится при commit (там же ловится нарушение UNIQUE)
        return driver


class ClientRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def all(self) -> list[Client]:
        return list(self.db.scalars(select(Client).order_by(Client.full_name)))

    def get(self, client_id: int) -> Client | None:
        return self.db.get(Client, client_id)

    def add(self, client: Client) -> Client:
        self.db.add(client)
        return client


class TripRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, trip_id: int) -> Trip | None:
        return self.db.get(Trip, trip_id)

    def search(self, *, text: str | None = None, status: TripStatus | None = None,
               car_class: CarClass | None = None, driver_id: int | None = None,
               sort: str = "date", order: str = "desc", page: int = 1, page_size: int = 10) -> tuple[list[Trip], int]:
        stmt = select(Trip).join(Trip.driver).join(Trip.client)
        if text:
            pattern = f"%{text}%"
            stmt = stmt.where(or_(Trip.pickup.ilike(pattern), Trip.destination.ilike(pattern),
                                  Client.full_name.ilike(pattern), Driver.full_name.ilike(pattern)))
        if status:
            stmt = stmt.where(Trip.status == status)
        if car_class:
            stmt = stmt.where(Driver.car_class == car_class)
        if driver_id:
            stmt = stmt.where(Trip.driver_id == driver_id)
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        column = TRIP_SORTS.get(sort, Trip.created_at)
        stmt = (stmt.options(joinedload(Trip.driver), joinedload(Trip.client))
                .order_by(column.desc() if order == "desc" else column.asc(), Trip.id.desc())
                .offset((page - 1) * page_size).limit(page_size))
        return list(self.db.scalars(stmt)), total

    def add(self, trip: Trip) -> Trip:
        self.db.add(trip)
        self.db.flush()
        return trip

    def delete(self, trip: Trip) -> None:
        self.db.delete(trip)
        self.db.flush()

    def summary(self) -> dict:
        row = self.db.execute(select(func.count(Trip.id), func.coalesce(func.sum(Trip.cost), 0))
                              .where(Trip.status == TripStatus.COMPLETED)).one()
        return {"trips": self.db.scalar(select(func.count(Trip.id))), "completed": row[0], "revenue": round(row[1], 2),
                "drivers": self.db.scalar(select(func.count(Driver.id))),
                "clients": self.db.scalar(select(func.count(Client.id)))}
