from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.train import Train, TrainStatus, User
from app.security import hash_password

TRAINS = [
    ("001А", "Москва - Санкт-Петербург", ["Москва", "Санкт-Петербург"], "2026-10-10T23:55", "2026-10-11T07:55", 14, 3200),
    ("752А", "Москва - Санкт-Петербург", ["Москва", "Тверь", "Санкт-Петербург"], "2026-10-10T06:50", "2026-10-10T10:45", 10, 4100),
    ("104В", "Москва - Казань", ["Москва", "Владимир", "Нижний Новгород", "Казань"], "2026-10-11T21:20", "2026-10-12T08:50", 15, 2400),
    ("026Ч", "Москва - Сочи", ["Москва", "Воронеж", "Ростов-на-Дону", "Сочи"], "2026-10-12T12:00", "2026-10-13T17:30", 18, 5600),
    ("002А", "Санкт-Петербург - Москва", ["Санкт-Петербург", "Москва"], "2026-10-12T23:55", "2026-10-13T07:55", 14, 3200),
    ("015Е", "Екатеринбург - Москва", ["Екатеринбург", "Пермь", "Киров", "Москва"], "2026-10-13T08:10", "2026-10-14T09:20", 16, 4800),
    ("727В", "Москва - Владимир", ["Москва", "Владимир"], "2026-10-10T08:00", "2026-10-10T09:45", 5, 1200),
    ("020У", "Москва - Ростов-на-Дону", ["Москва", "Воронеж", "Ростов-на-Дону"], "2026-10-11T22:50", "2026-10-12T15:00", 15, 3500),
]


def seed(db: Session) -> None:
    if db.scalar(select(func.count(Train.id))):
        return
    for i, (number, route, stations, dep, arr, wagons, price) in enumerate(TRAINS):
        db.add(Train(number=number, route=route, stations=stations, departure_time=datetime.fromisoformat(dep),
                     arrival_time=datetime.fromisoformat(arr), wagons_count=wagons, price=price,
                     status=TrainStatus.CANCELLED if i == 6 else TrainStatus.SCHEDULED))
    if not db.scalar(select(func.count(User.id))):
        db.add(User(username="admin", password_hash=hash_password("admin123"), role="ADMIN"))
    db.commit()
