"""python manage.py seed_data — тестовые данные (24 поезда, 12 станций, 5 маршрутов, пассажиры, билеты, пользователи)."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from railway.models import Passenger, Route, RouteStop, Station, Ticket, Train

STATIONS = [("Москва Ленинградская", "Москва"), ("Тверь", "Тверь"), ("Бологое", "Бологое"),
            ("Санкт-Петербург Главный", "Санкт-Петербург"), ("Москва Казанская", "Москва"), ("Владимир", "Владимир"),
            ("Нижний Новгород", "Нижний Новгород"), ("Казань", "Казань"), ("Москва Курская", "Москва"),
            ("Воронеж", "Воронеж"), ("Ростов-Главный", "Ростов-на-Дону"), ("Сочи", "Сочи")]
ROUTES = {
    "Москва — Санкт-Петербург": [(0, 0), (1, 100), (2, 220), (3, 480)],
    "Москва — Казань": [(4, 0), (5, 140), (6, 330), (7, 690)],
    "Москва — Сочи": [(8, 0), (9, 430), (10, 960), (11, 1770)],
    "Москва — Нижний Новгород": [(4, 0), (5, 105), (6, 240)],
    "Москва — Ростов-на-Дону": [(8, 0), (9, 420), (10, 960)],
}
TRAINS = [  # (номер, название, маршрут, тип, мест, цена)
    ("001А", "Красная стрела", 0, "fast", 360, 3200), ("003А", "Экспресс", 0, "fast", 400, 3000),
    ("752А", "Сапсан", 0, "high_speed", 600, 4100), ("754А", "Сапсан", 0, "high_speed", 600, 4300),
    ("104В", "Татарстан", 1, "fast", 380, 2400), ("002Г", "Премиум", 1, "fast", 300, 3600),
    ("026Ч", "Москва — Сочи", 2, "fast", 540, 5600), ("102М", "Москва — Адлер", 2, "passenger", 700, 3900),
    ("723Н", "Ласточка", 3, "high_speed", 450, 1300), ("725Н", "Ласточка", 3, "high_speed", 450, 1300),
    ("020У", "Тихий Дон", 4, "fast", 420, 3500), ("092С", "Ростов", 4, "passenger", 650, 2600),
]


class Command(BaseCommand):
    help = "Заполнить базу тестовыми данными"

    @transaction.atomic
    def handle(self, *args, **options):
        if Train.objects.exists():
            self.stdout.write("Данные уже есть — пропускаю.")
            return
        stations = [Station.objects.create(name=n, city=c) for n, c in STATIONS]
        routes = []
        for name, stops in ROUTES.items():
            route = Route.objects.create(name=name)
            for order, (station_index, minutes) in enumerate(stops, start=1):
                RouteStop.objects.create(route=route, station=stations[station_index], order=order, minutes_from_start=minutes)
            routes.append(route)

        start = timezone.now().replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
        trains = []
        for day in range(2):                       # 12 поездов × 2 даты = 24 поезда
            for i, (number, name, route_index, kind, seats, price) in enumerate(TRAINS):
                trains.append(Train.objects.create(
                    number=number if day == 0 else f"{number[:3]}{chr(ord(number[3]) + 1)}" if len(number) == 4 else number + "Б",
                    name=name, route=routes[route_index], train_type=kind,
                    departure=start + timedelta(days=day, hours=2 * i), seats_total=seats,
                    base_price=Decimal(price + day * 200),
                    status="cancelled" if (day, i) == (1, 11) else ("delayed" if (day, i) == (0, 6) else "scheduled")))

        names = ["Иванов Иван", "Петрова Анна", "Сидоров Пётр", "Кузнецова Мария", "Смирнов Алексей",
                 "Волкова Елена", "Морозов Дмитрий", "Новикова Ольга", "Фёдоров Игорь", "Соколова Дарья"]
        passengers = [Passenger.objects.create(full_name=n, passport=f"45{i:02d} {100000 + i}") for i, n in enumerate(names)]
        for k in range(30):
            train = trains[k % 9]
            Ticket.objects.create(train=train, passenger=passengers[k % 10], seat=k + 1, price=train.base_price,
                                  status="returned" if k % 13 == 12 else "paid")

        admin = User.objects.create_superuser("admin", "admin@example.com", "admin12345")
        user = User.objects.create_user("user", "user@example.com", "user12345")
        passengers[0].user = user
        passengers[0].save()
        self.stdout.write(self.style.SUCCESS(
            f"Создано: станций {len(stations)}, маршрутов {len(routes)}, поездов {len(trains)}, "
            f"пассажиров {len(passengers)}, билетов 30, пользователи {admin.username}/{user.username}"))
