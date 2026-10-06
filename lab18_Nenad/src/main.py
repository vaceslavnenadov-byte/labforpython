"""
ЛР №18. Вариант 10. Продажа железнодорожных билетов (консольный интерфейс).
Запуск из папки lab18_Nenad: python -m src.main
"""

from datetime import datetime, timedelta

from src.exceptions import RailwayError
from src.repositories.sqlite_repository import RouteRepository, TicketRepository, connect
from src.services.ticket_service import TicketService


class ConsoleNotifier:
    def send(self, passenger: str, message: str) -> None:
        print(f"[SMS → {passenger}] {message}")


def build_service(path: str = "railway_tickets.db") -> TicketService:
    connection = connect(path)
    service = TicketService(RouteRepository(connection), TicketRepository(connection), ConsoleNotifier())
    if not service.routes.find_all():
        base = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(days=2)
        for i, (number, a, b, seats, price) in enumerate([
            ("001А", "Москва", "Санкт-Петербург", 36, 3200), ("752А", "Москва", "Санкт-Петербург", 60, 4100),
            ("104В", "Москва", "Казань", 36, 2400), ("026Ч", "Москва", "Сочи", 4, 5600),
        ]):
            service.create_route(number, a, b, base + timedelta(hours=5 * i), seats, price)
    return service


def main() -> None:
    service = build_service()
    while True:
        print("\n1. Все рейсы  2. Поиск  3. Свободные места  4. Купить  5. Вернуть  6. Мои билеты  7. Новый рейс  0. Выход")
        choice = input("> ").strip()
        try:
            if choice == "1":
                for r in service.routes.find_all():
                    print(f"  №{r.id} {r.train_number} {r.from_city} → {r.to_city} {r.departure:%d.%m %H:%M} "
                          f"{r.price} руб., свободно {len(service.free_seats(r.id))}/{r.seats}")
            elif choice == "2":
                for r in service.search(input("Откуда: "), input("Куда: "), input("Дата ГГГГ-ММ-ДД (Enter — любая): ") or None):
                    print(f"  №{r.id} {r.train_number} {r.departure:%d.%m %H:%M} {r.price} руб.")
            elif choice == "3":
                print(service.free_seats(int(input("№ рейса: "))))
            elif choice == "4":
                seat = input("Место (Enter — любое): ").strip()
                ticket = service.sell_ticket(int(input("№ рейса: ")), input("Пассажир: "), int(seat) if seat else None)
                print(f"Продан билет №{ticket.id}, место {ticket.seat}")
            elif choice == "5":
                print(f"К возврату: {service.return_ticket(int(input('№ билета: ')))} руб.")
            elif choice == "6":
                for t in service.passenger_tickets(input("Пассажир: ")):
                    print(f"  №{t.id} рейс {t.route_id}, место {t.seat}, {t.price} руб., {t.status.value}")
            elif choice == "7":
                route = service.create_route(input("Поезд: "), input("Откуда: "), input("Куда: "),
                                             datetime.fromisoformat(input("Отправление (2026-12-01T10:00): ")),
                                             int(input("Мест: ")), float(input("Цена: ")))
                print("Создан рейс №", route.id)
            elif choice == "0":
                break
        except (RailwayError, ValueError) as error:
            print("Ошибка:", error)


if __name__ == "__main__":
    main()
