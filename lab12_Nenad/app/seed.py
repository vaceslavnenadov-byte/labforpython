"""Тестовые данные."""

from app.models import CarClass, DriverStatus
from app.services.services import TaxiService


def seed(service: TaxiService) -> None:
    clients = [("Иванов Иван", "+79001110001", "ivanov@mail.ru"), ("Петрова Анна", "+79001110002", None),
               ("Сидоров Павел", "+79001110003", "sidorov@mail.ru"), ("Кузнецова Мария", "+79001110004", None),
               ("Андреев Алексей", "+79001110005", "andreev@mail.ru")]
    for name, phone, email in clients:
        service.create_client(name, phone, email)

    drivers = [("Смирнов Олег", "+79002220001", "77 11 000001", 12), ("Волков Дмитрий", "+79002220002", "77 11 000002", 5),
               ("Морозов Сергей", "+79002220003", "77 11 000003", 8), ("Новиков Артём", "+79002220004", "77 11 000004", 2)]
    for d in drivers:
        service.create_driver(*d)

    service.add_car_to_driver(1, "А001АА777", "Mercedes E-класс", CarClass.BUSINESS)
    service.add_car_to_driver(1, "К123КК777", "Skoda Octavia", CarClass.COMFORT)
    service.add_car_to_driver(2, "К123КК777", "Skoda Octavia", CarClass.COMFORT)   # одна машина — два водителя
    service.add_car_to_driver(3, "В555ВВ750", "Kia Rio", CarClass.ECONOMY)
    service.add_car_to_driver(4, "Е777ЕЕ799", "Hyundai Solaris", CarClass.ECONOMY)

    trips = [(1, "Тверская, 1", "Шереметьево", 35.0, 50, CarClass.BUSINESS, 5),
             (2, "Арбат, 10", "Курский вокзал", 6.5, 22, CarClass.ECONOMY, 4),
             (3, "Ленинский пр., 50", "Москва-Сити", 12.0, 30, CarClass.COMFORT, 5),
             (1, "Шереметьево", "Тверская, 1", 34.0, 45, CarClass.ECONOMY, 3)]
    for client_id, a, b, km, minutes, cls, mark in trips:
        trip = service.create_trip(client_id, a, b, km, minutes, cls)
        service.start_trip(trip.id)
        service.complete_trip(trip.id, driver_rating=mark)
    service.create_trip(4, "Пресненская наб., 8", "Внуково", 28.0, 40, CarClass.ECONOMY)  # активная поездка
    service.set_driver_status(2, DriverStatus.OFFLINE)
