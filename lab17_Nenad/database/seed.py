"""Тестовые данные: 10 станций, 16 поездов, 6 пользователей, билеты (всего > 20 записей)."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Station, Ticket, Train, User, WagonType

STATIONS = [("Москва Ленинградская", "Москва"), ("Санкт-Петербург Главный", "Санкт-Петербург"),
            ("Москва Казанская", "Москва"), ("Казань", "Казань"), ("Нижний Новгород", "Нижний Новгород"),
            ("Москва Курская", "Москва"), ("Сочи", "Сочи"), ("Воронеж", "Воронеж"),
            ("Екатеринбург-Пасс.", "Екатеринбург"), ("Владимир", "Владимир")]
TRAINS = [  # номер, название, откуда, куда, часы в пути, цена, места сид/купе/св
    ("001А", "Красная стрела", 0, 1, 8, 3200, 0, 36, 18), ("752А", "Сапсан", 0, 1, 4, 4100, 60, 0, 0),
    ("002А", "Красная стрела", 1, 0, 8, 3200, 0, 36, 18), ("753А", "Сапсан", 1, 0, 4, 4100, 60, 0, 0),
    ("104В", "Татарстан", 2, 3, 11, 2400, 0, 36, 18), ("105Ж", "Татарстан", 3, 2, 11, 2400, 0, 36, 18),
    ("724Н", "Ласточка", 2, 4, 4, 1500, 60, 0, 0), ("723Н", "Ласточка", 4, 2, 4, 1500, 60, 0, 0),
    ("026Ч", "Москва — Сочи", 5, 6, 29, 5600, 0, 36, 18), ("025Ч", "Сочи — Москва", 6, 5, 29, 5600, 0, 36, 18),
    ("020У", "Воронеж", 5, 7, 8, 2100, 60, 36, 0), ("019У", "Воронеж", 7, 5, 8, 2100, 60, 36, 0),
    ("016Е", "Урал", 2, 8, 25, 4800, 0, 36, 18), ("015Е", "Урал", 8, 2, 25, 4800, 0, 36, 18),
    ("727В", "Ласточка", 5, 9, 2, 1200, 60, 0, 0), ("728В", "Ласточка", 9, 5, 2, 1200, 60, 0, 0),
]


async def seed(session: AsyncSession) -> None:
    if await session.scalar(select(func.count(Station.id))):
        return
    stations = [Station(name=n, city=c) for n, c in STATIONS]
    session.add_all(stations)
    await session.flush()
    start = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
    trains = []
    for i, (number, name, a, b, hours, price, seated, coupe, sv) in enumerate(TRAINS):
        departure = start + timedelta(hours=3 * i)
        trains.append(Train(number=number, name=name, from_station_id=stations[a].id, to_station_id=stations[b].id,
                            departure=departure, arrival=departure + timedelta(hours=hours), base_price=price,
                            seats_seated=seated, seats_coupe=coupe, seats_sv=sv))
    session.add_all(trains)
    users = [User(telegram_id=1000 + i, username=f"user{i}", full_name=f"Тестовый пассажир {i}") for i in range(6)]
    session.add_all(users)
    await session.flush()
    for k in range(12):
        train = trains[k % 6]
        wagon = WagonType.SEATED if train.seats_seated else WagonType.COUPE
        session.add(Ticket(user_id=users[k % 6].id, train_id=train.id, wagon_type=wagon, seat=k + 1,
                           passenger_name=users[k % 6].full_name, price=train.price(wagon)))
    await session.commit()
