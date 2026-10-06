"""Генерация 24 документов «поезд» для коллекции trains."""

from datetime import datetime, timedelta

ROUTES = [
    ("Красная стрела", "скорый", [("Москва Ленинградская", "Москва"), ("Санкт-Петербург Главный", "Санкт-Петербург")], 8 * 60, 3200),
    ("Сапсан", "высокоскоростной", [("Москва Ленинградская", "Москва"), ("Тверь", "Тверь"), ("Санкт-Петербург Главный", "Санкт-Петербург")], 4 * 60, 4100),
    ("Татарстан", "скорый", [("Москва Казанская", "Москва"), ("Владимир", "Владимир"), ("Нижний Новгород", "Нижний Новгород"), ("Казань", "Казань")], 11 * 60, 2400),
    ("Ласточка", "пассажирский", [("Москва Курская", "Москва"), ("Владимир", "Владимир")], 105, 1200),
    ("Тихий Дон", "скорый", [("Москва Казанская", "Москва"), ("Воронеж", "Воронеж"), ("Ростов-Главный", "Ростов-на-Дону")], 16 * 60, 3500),
    ("Москва — Сочи", "скорый", [("Москва Курская", "Москва"), ("Воронеж", "Воронеж"), ("Ростов-Главный", "Ростов-на-Дону"), ("Сочи", "Сочи")], 29 * 60, 5600),
    ("Урал", "скорый", [("Москва Ярославская", "Москва"), ("Нижний Новгород", "Нижний Новгород"), ("Екатеринбург-Пасс.", "Екатеринбург")], 25 * 60, 4800),
    ("Невский экспресс", "высокоскоростной", [("Санкт-Петербург Главный", "Санкт-Петербург"), ("Москва Ленинградская", "Москва")], 4 * 60, 4300),
]
WAGON_SETS = {
    "скорый": [("coupe", 36), ("coupe", 36), ("sv", 18)],
    "высокоскоростной": [("seated", 60), ("seated", 60), ("seated", 60)],
    "пассажирский": [("seated", 60), ("seated", 60)],
}


def generate(count: int = 24) -> list[dict]:
    start = datetime(2026, 10, 10, 6, 0)
    documents = []
    for i in range(count):
        name, category, stations, minutes, price = ROUTES[i % len(ROUTES)]
        departure = start + timedelta(hours=7 * i)
        step = minutes / (len(stations) - 1)
        stops = []
        for k, (station, city) in enumerate(stations):
            moment = departure + timedelta(minutes=step * k)
            stops.append({"station": station, "city": city,
                          "arrival": None if k == 0 else moment.isoformat(timespec="minutes"),
                          "departure": None if k == len(stations) - 1 else (moment + timedelta(minutes=2 if k else 0)).isoformat(timespec="minutes")})
        wagons = [{"number": n, "type": t, "seats": s, "booked": list(range(1, (i * 7 + n * 5) % s + 1))}
                  for n, (t, s) in enumerate(WAGON_SETS[category], start=1)]
        status = "cancelled" if i % 11 == 10 else ("departed" if i < 3 else "scheduled")
        documents.append({"number": f"{100 + i}{'АБВГДЕЖИКЛМН'[i % 12]}", "name": name, "category": category,
                          "stops": stops, "wagons": wagons, "base_price": price + (i % 4) * 150, "status": status})
    return documents
