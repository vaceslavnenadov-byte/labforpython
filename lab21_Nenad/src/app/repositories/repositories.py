"""Repository-слой: доступ к данным через SQLAlchemy."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.app.models import Car, CarClass, Driver, DriverStatus, Notification, Order, OrderStatus, OutboxEvent, User

ACTIVE = (OrderStatus.ASSIGNED, OrderStatus.IN_PROGRESS)
ORDER_SORTS = {"created_at": Order.created_at, "price": Order.price, "distance": Order.distance_km}


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(func.lower(User.email) == email.lower()))

    def get(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user


class CarRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def all(self) -> list[Car]:
        return list(self.db.scalars(select(Car).order_by(Car.id)))

    def get(self, car_id: int) -> Car | None:
        return self.db.get(Car, car_id)

    def by_plate(self, plate: str) -> Car | None:
        return self.db.scalar(select(Car).where(Car.plate == plate))

    def add(self, car: Car) -> Car:
        self.db.add(car)
        self.db.flush()
        return car


class DriverRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, driver_id: int) -> Driver | None:
        return self.db.get(Driver, driver_id)

    def by_phone_or_license(self, phone: str, license_number: str) -> Driver | None:
        return self.db.scalar(select(Driver).where((Driver.phone == phone) | (Driver.license_number == license_number)))

    def search(self, status: DriverStatus | None, car_class: CarClass | None, sort: str) -> list[Driver]:
        stmt = select(Driver).outerjoin(Driver.car)
        if status:
            stmt = stmt.where(Driver.status == status)
        if car_class:
            stmt = stmt.where(Car.car_class == car_class)
        stmt = stmt.order_by(Driver.rating.desc() if sort == "rating" else Driver.full_name, Driver.id)
        return list(self.db.scalars(stmt).unique())

    def find_free(self, car_class: CarClass) -> Driver | None:
        """Лучший свободный водитель с машиной нужного класса; строка блокируется до конца транзакции
        (SELECT ... FOR UPDATE SKIP LOCKED в PostgreSQL), чтобы два заказа не получили одного водителя."""
        stmt = (select(Driver).join(Driver.car)
                .where(Driver.status == DriverStatus.FREE, Car.car_class == car_class)
                .order_by(Driver.rating.desc(), Driver.id).limit(1)
                .with_for_update(skip_locked=True, of=Driver))
        return self.db.scalars(stmt).first()

    def count_by_status(self) -> dict[str, int]:
        rows = self.db.execute(select(Driver.status, func.count()).group_by(Driver.status)).all()
        return {status.value: count for status, count in rows}

    def add(self, driver: Driver) -> Driver:
        self.db.add(driver)
        self.db.flush()
        return driver


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, order_id: int) -> Order | None:
        return self.db.get(Order, order_id)

    def active_for_passenger(self, passenger_id: int) -> Order | None:
        return self.db.scalar(select(Order).where(Order.passenger_id == passenger_id, Order.status.in_(ACTIVE)))

    def search(self, *, passenger_id: int | None, status: OrderStatus | None, text: str | None,
               sort: str, order: str, skip: int, limit: int) -> tuple[list[Order], int]:
        stmt = select(Order)
        if passenger_id:
            stmt = stmt.where(Order.passenger_id == passenger_id)
        if status:
            stmt = stmt.where(Order.status == status)
        if text:
            pattern = f"%{text.lower()}%"
            stmt = stmt.where(func.lower(Order.pickup).like(pattern) | func.lower(Order.destination).like(pattern))
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        column = ORDER_SORTS[sort]
        stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), Order.id).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).unique()), total

    def add(self, order: Order) -> Order:
        self.db.add(order)
        self.db.flush()
        return order

    def delete(self, order: Order) -> None:
        self.db.delete(order)

    def statistics(self) -> dict:
        count, revenue, avg_price, avg_distance = self.db.execute(
            select(func.count(Order.id), func.coalesce(func.sum(Order.price), 0),
                   func.coalesce(func.avg(Order.price), 0), func.coalesce(func.avg(Order.distance_km), 0))
            .where(Order.status == OrderStatus.COMPLETED)).one()
        by_status = dict(self.db.execute(select(Order.status, func.count()).group_by(Order.status)).all())
        by_class = dict(self.db.execute(select(Order.car_class, func.count())
                                        .where(Order.status == OrderStatus.COMPLETED)
                                        .group_by(Order.car_class)).all())
        return {"completed": count, "revenue": round(revenue, 2), "average_price": round(avg_price, 2),
                "average_distance": round(avg_distance, 2),
                "orders_by_status": {s.value: n for s, n in by_status.items()},
                "completed_by_class": {c.value: n for c, n in by_class.items()}}


class OutboxRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, event: OutboxEvent) -> None:
        self.db.add(event)

    def pending(self, limit: int = 100) -> list[OutboxEvent]:
        return list(self.db.scalars(select(OutboxEvent).where(OutboxEvent.published.is_(False))
                                    .order_by(OutboxEvent.id).limit(limit)))


class NotificationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def exists(self, event_id: str) -> bool:
        return self.db.scalar(select(Notification.id).where(Notification.event_id == event_id)) is not None

    def add(self, notification: Notification) -> None:
        self.db.add(notification)

    def for_user(self, user_id: int) -> list[Notification]:
        return list(self.db.scalars(select(Notification).where(Notification.user_id == user_id)
                                    .order_by(Notification.id.desc())))
