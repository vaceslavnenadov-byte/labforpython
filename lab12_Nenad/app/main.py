"""
ЛР №12. SQLAlchemy ORM + PostgreSQL. Вариант 10 — Такси (Client, Driver, Trip).

Запуск из папки lab12_Nenad:  python -m app.main
Строка подключения: переменная DATABASE_URL (см. .env.example).
"""

from app.database import create_db_engine, create_session_factory, get_database_url
from app.exceptions import TaxiError
from app.models import Base, CarClass, TripStatus
from app.seed import seed
from app.services.services import TaxiService, calculate_cost

CLASSES = {"1": CarClass.ECONOMY, "2": CarClass.COMFORT, "3": CarClass.BUSINESS}


def ask_int(prompt: str) -> int:
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("  Введите целое число.")


def ask_float(prompt: str) -> float:
    while True:
        try:
            return float(input(prompt).replace(",", "."))
        except ValueError:
            print("  Введите число.")


def ask_class() -> CarClass:
    while True:
        value = CLASSES.get(input("Класс (1 — эконом, 2 — комфорт, 3 — бизнес): ").strip())
        if value:
            return value
        print("  Неизвестный класс.")


def show(items) -> None:
    if not items:
        print("  (пусто)")
    for item in items:
        print("  ", item)


def main() -> None:
    url = get_database_url()
    engine = create_db_engine(url)
    Base.metadata.create_all(engine)
    service = TaxiService(create_session_factory(engine))
    print(f"Подключено: {engine.url.render_as_string(hide_password=True)}")
    if service.statistics()["clients"] == 0:
        seed(service)
        print("База была пустой — добавлены тестовые данные.")

    actions = {
        "1": "Клиенты (страница)", "2": "Добавить клиента", "3": "Изменить клиента", "4": "Удалить клиента",
        "5": "Поиск клиентов по ФИО", "6": "Поездки клиента (связь 1:N)", "7": "Водители (сортировка)",
        "8": "Водители и их машины (M:N)", "9": "Заказать поездку (транзакция)", "10": "Начать поездку",
        "11": "Завершить поездку (транзакция)", "12": "Отменить поездку", "13": "Фильтр поездок",
        "14": "Расчёт стоимости", "15": "Статистика (агрегаты)", "16": "Поездка по id",
    }
    while True:
        print("\n===== ТАКСИ (SQLAlchemy) =====")
        for key, title in actions.items():
            print(f"{key}. {title}")
        print("0. Выход")
        choice = input("Выберите действие: ").strip()
        try:
            if choice == "1":
                show(service.list_clients(ask_int("Страница: "), 5))
            elif choice == "2":
                print("Создан:", service.create_client(input("ФИО: "), input("Телефон: "), input("Email: ") or None))
            elif choice == "3":
                client_id = ask_int("id: ")
                fields = {k: v for k, v in {"full_name": input("Новое ФИО (Enter — без изменений): "),
                                            "phone": input("Новый телефон (Enter — без изменений): ")}.items() if v}
                print("Изменён:", service.update_client(client_id, **fields))
            elif choice == "4":
                service.delete_client(ask_int("id: "))
                print("Удалён.")
            elif choice == "5":
                show(service.search_clients(input("Часть ФИО: ")))
            elif choice == "6":
                show(service.client_trips(ask_int("id клиента: ")))
            elif choice == "7":
                field = input("Поле (rating/experience/name): ").strip() or "rating"
                show(service.drivers_sorted(field, input("По убыванию? (д/н): ").strip() != "н"))
            elif choice == "8":
                for driver in service.drivers_with_cars():
                    print(f"   {driver} → {', '.join(map(repr, driver.cars)) or 'нет машин'}")
            elif choice == "9":
                trip = service.create_trip(ask_int("id клиента: "), input("Откуда: "), input("Куда: "),
                                           ask_float("Расстояние, км: "), ask_int("Время в пути, мин: "), ask_class())
                print("Создана:", trip, "| водитель:", trip.driver.full_name, "| машина:", trip.car.plate)
            elif choice == "10":
                print("Начата:", service.start_trip(ask_int("id поездки: ")))
            elif choice == "11":
                trip_id = ask_int("id поездки: ")
                mark = input("Оценка водителю 1–5 (Enter — без оценки): ").strip()
                print("Завершена:", service.complete_trip(trip_id, driver_rating=int(mark) if mark else None))
            elif choice == "12":
                print("Отменена:", service.cancel_trip(ask_int("id поездки: ")))
            elif choice == "13":
                status = input("Статус (created/assigned/in_progress/completed/cancelled, Enter — любой): ").strip()
                min_cost = input("Мин. стоимость (Enter — любая): ").strip()
                sort = input("Сортировка (date/cost/distance): ").strip() or "date"
                show(service.filter_trips(status=TripStatus(status) if status else None,
                                          min_cost=float(min_cost) if min_cost else None, sort=sort))
            elif choice == "14":
                print(f"Стоимость: {calculate_cost(ask_class(), ask_float('Км: '), ask_int('Минут: ')):.2f} руб.")
            elif choice == "15":
                for key, value in service.statistics().items():
                    print(f"  {key}: {value}")
            elif choice == "16":
                trip = service.get_trip(ask_int("id: "))
                print(trip, "| клиент:", trip.client.full_name,
                      "| водитель:", trip.driver.full_name if trip.driver else "-")
            elif choice == "0":
                break
            else:
                print("Неизвестный пункт.")
        except TaxiError as error:
            print(f"Ошибка ({type(error).__name__}): {error}")
        except (ValueError, KeyError) as error:
            print("Некорректный ввод:", error)


if __name__ == "__main__":
    main()
