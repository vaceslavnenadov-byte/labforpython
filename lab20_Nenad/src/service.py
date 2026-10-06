"""Бизнес-логика такси."""

import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.cache import Cache
from src.models import CarClass, Driver, Ride, RideStatus
from src.schemas import DriverIn, RideIn, RideOut

logger = logging.getLogger("taxi.service")
TARIFFS = {CarClass.ECONOMY: (99, 14), CarClass.COMFORT: (149, 19), CarClass.BUSINESS: (299, 32)}
TRANSITIONS = {
    RideStatus.CREATED: {RideStatus.IN_PROGRESS, RideStatus.CANCELLED},
    RideStatus.IN_PROGRESS: {RideStatus.COMPLETED, RideStatus.CANCELLED},
    RideStatus.COMPLETED: set(),
    RideStatus.CANCELLED: set(),
}


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


def calculate_cost(car_class: CarClass, distance_km: float) -> float:
    if distance_km <= 0:
        raise ValueError("distance must be positive")
    base, per_km = TARIFFS[car_class]
    return round(base + per_km * distance_km, 2)


class TaxiService:
    def __init__(self, session: Session, cache: Cache) -> None:
        self.session = session
        self.cache = cache

    def create_driver(self, data: DriverIn) -> Driver:
        driver = Driver(**data.model_dump())
        self.session.add(driver)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise Conflict(f"Car plate {data.car_plate} already registered") from None
        return driver

    def list_drivers(self) -> list[Driver]:
        return list(self.session.scalars(select(Driver).order_by(Driver.id)))

    def create_ride(self, data: RideIn) -> Ride:
        driver = self.session.get(Driver, data.driver_id)
        if driver is None:
            raise NotFound(f"Driver {data.driver_id} not found")
        busy = self.session.scalar(select(func.count(Ride.id)).where(
            Ride.driver_id == driver.id, Ride.status.in_([RideStatus.CREATED, RideStatus.IN_PROGRESS])))
        if busy:
            raise Conflict(f"Driver {driver.id} already has an active ride")
        ride = Ride(**data.model_dump(), cost=calculate_cost(driver.car_class, data.distance_km))
        self.session.add(ride)
        self.session.commit()
        logger.info("ride %s created for %s, cost %.2f", ride.id, ride.passenger, ride.cost)
        return ride

    def get_ride(self, ride_id: int) -> tuple[dict, bool]:
        key = f"ride:{ride_id}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached, True
        ride = self.session.get(Ride, ride_id)
        if ride is None:
            raise NotFound(f"Ride {ride_id} not found")
        data = RideOut.model_validate(ride).model_dump(mode="json")
        self.cache.set(key, data)
        return data, False

    def list_rides(self, status: RideStatus | None = None, limit: int = 50) -> list[Ride]:
        stmt = select(Ride).order_by(Ride.id.desc()).limit(limit)
        if status:
            stmt = stmt.where(Ride.status == status)
        return list(self.session.scalars(stmt).unique())

    def change_status(self, ride_id: int, status: RideStatus) -> Ride:
        ride = self.session.get(Ride, ride_id)
        if ride is None:
            raise NotFound(f"Ride {ride_id} not found")
        if status not in TRANSITIONS[ride.status]:
            raise Conflict(f"Transition {ride.status.value} -> {status.value} is not allowed")
        ride.status = status
        if status == RideStatus.CANCELLED:
            ride.cost = 0
        self.session.commit()
        self.cache.delete(f"ride:{ride_id}")
        logger.info("ride %s -> %s", ride_id, status.value)
        return ride

    def stats(self) -> dict:
        count, revenue = self.session.execute(
            select(func.count(Ride.id), func.coalesce(func.sum(Ride.cost), 0))
            .where(Ride.status == RideStatus.COMPLETED)).one()
        return {"completed_rides": count, "revenue": round(revenue, 2), "drivers": len(self.list_drivers())}
