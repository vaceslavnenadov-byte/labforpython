"""Repository: запросы SQLAlchemy. Роутеры напрямую с БД не работают."""

from datetime import date, datetime, time

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.train import Train, TrainStatus

SORT_FIELDS = {"number": Train.number, "departure_time": Train.departure_time,
               "price": Train.price, "wagons_count": Train.wagons_count}


class TrainRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, train_id: int) -> Train | None:
        return self.db.get(Train, train_id)

    def get_by_number(self, number: str) -> Train | None:
        return self.db.scalar(select(Train).where(Train.number == number))

    def list_trains(self, *, status: TrainStatus | None, route: str | None, departure_date: date | None,
             min_price: float | None, max_price: float | None, sort: str, order: str,
             skip: int, limit: int) -> tuple[list[Train], int]:
        conditions = []
        if status:
            conditions.append(Train.status == status)
        if route:
            conditions.append(Train.route.ilike(f"%{route}%"))
        if departure_date:
            start = datetime.combine(departure_date, time.min)
            conditions.append(Train.departure_time.between(start, datetime.combine(departure_date, time.max)))
        if min_price is not None:
            conditions.append(Train.price >= min_price)
        if max_price is not None:
            conditions.append(Train.price <= max_price)
        column = SORT_FIELDS[sort]
        total = self.db.scalar(select(func.count()).select_from(Train).where(*conditions))
        stmt = (select(Train).where(*conditions)
                .order_by(column.desc() if order == "desc" else column.asc(), Train.id)
                .offset(skip).limit(limit))
        return list(self.db.scalars(stmt)), total

    def search(self, query: str) -> list[Train]:
        pattern = f"%{query}%"
        stmt = select(Train).where(or_(Train.number.ilike(pattern), Train.route.ilike(pattern))).order_by(Train.departure_time)
        found = list(self.db.scalars(stmt))
        # stations хранится в JSON — ищем по нему на стороне Python, чтобы код работал и в SQLite, и в PostgreSQL
        rest = self.db.scalars(select(Train).where(Train.id.not_in([t.id for t in found]) if found else True))
        found += [t for t in rest if any(query.lower() in s.lower() for s in t.stations)]
        return found

    def add(self, train: Train) -> Train:
        self.db.add(train)
        self.db.commit()
        self.db.refresh(train)
        return train

    def save(self, train: Train) -> Train:
        self.db.commit()
        self.db.refresh(train)
        return train

    def delete(self, train: Train) -> None:
        self.db.delete(train)
        self.db.commit()

    def statistics(self) -> dict:
        row = self.db.execute(select(func.count(Train.id), func.avg(Train.price), func.min(Train.price),
                                     func.max(Train.price), func.sum(Train.wagons_count))).one()
        by_status = dict(self.db.execute(select(Train.status, func.count()).group_by(Train.status)).all())
        by_route = dict(self.db.execute(select(Train.route, func.count()).group_by(Train.route)).all())
        durations = [(t.arrival_time - t.departure_time).total_seconds() / 3600 for t in self.db.scalars(select(Train))]
        return {
            "total": row[0], "average_price": round(row[1] or 0, 2), "min_price": row[2] or 0,
            "max_price": row[3] or 0, "total_wagons": row[4] or 0,
            "average_duration_hours": round(sum(durations) / len(durations), 2) if durations else 0,
            "by_status": {s.value: n for s, n in by_status.items()}, "by_route": by_route,
        }
