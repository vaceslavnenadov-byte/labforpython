from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.models.models import CarClass, Client, Driver, Trip, TripStatus
from app.services.services import calculate_cost


def seed(db) -> None:
    if db.scalar(select(func.count(Driver.id))):
        return
    drivers = [
        Driver(full_name="Смирнов Олег", phone="+79002220001", car_model="Mercedes E-класс", car_plate="А001АА777", car_class=CarClass.BUSINESS, rating=4.9),
        Driver(full_name="Волков Дмитрий", phone="+79002220002", car_model="Skoda Octavia", car_plate="К123КК777", car_class=CarClass.COMFORT, rating=4.7),
        Driver(full_name="Морозов Сергей", phone="+79002220003", car_model="Kia Rio", car_plate="В555ВВ750", car_class=CarClass.ECONOMY, rating=4.5),
        Driver(full_name="Новиков Артём", phone="+79002220004", car_model="Hyundai Solaris", car_plate="Е777ЕЕ799", car_class=CarClass.ECONOMY, rating=4.8),
    ]
    clients = [
        Client(full_name="Иванов Иван", phone="+79001110001", email="ivanov@mail.ru"),
        Client(full_name="Петрова Анна", phone="+79001110002"),
        Client(full_name="Сидоров Павел", phone="+79001110003", email="sidorov@mail.ru"),
        Client(full_name="Кузнецова Мария", phone="+79001110004"),
    ]
    db.add_all(drivers + clients)
    db.flush()
    routes = [("Тверская, 1", "Шереметьево", 35, 50), ("Арбат, 10", "Курский вокзал", 6.5, 22),
              ("Ленинский пр., 50", "Москва-Сити", 12, 30), ("Шереметьево", "Тверская, 1", 34, 45),
              ("ВДНХ", "Парк Горького", 14, 35), ("Внуково", "Пресненская наб., 8", 28, 40),
              ("Белорусский вокзал", "Сокольники", 9, 25), ("Лужники", "Китай-город", 8, 20),
              ("Домодедово", "Павелецкий вокзал", 42, 55), ("Измайлово", "Арбат, 10", 15, 33)]
    statuses = [TripStatus.COMPLETED] * 6 + [TripStatus.CANCELLED, TripStatus.IN_PROGRESS, TripStatus.CREATED, TripStatus.CREATED]
    start = datetime(2026, 10, 1, 9, 0)
    for i, (a, b, km, minutes) in enumerate(routes):
        driver, client = drivers[i % 4], clients[i % 4]
        cost = 0 if statuses[i] == TripStatus.CANCELLED else calculate_cost(driver.car_class, km, minutes)
        db.add(Trip(client=client, driver=driver, pickup=a, destination=b, distance_km=km, duration_min=minutes,
                    cost=cost, status=statuses[i], created_at=start + timedelta(hours=9 * i)))
    db.commit()
