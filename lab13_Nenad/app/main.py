"""
ЛР №13. MongoDB + Redis. Вариант 10 — Железная дорога (поезда).

Запуск:   python -m app.main            (нужны MongoDB и Redis, см. docker-compose.yml)
          python -m app.main --mock     (mongomock + fakeredis, без серверов)
"""

import argparse
import json
from datetime import datetime

from app.cache import RedisCache
from app.models import ValidationError
from app.mongodb import get_database
from app.redis_client import get_redis
from app.repository import MongoRepository, NotFoundError
from app.seed import generate
from app.service import TrainService


def dump(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def brief(docs) -> None:
    if not docs:
        print("  (нет данных)")
    for d in docs:
        print(f"  id={d.get('_id')} {d.get('number', ''):<6} {d.get('name', ''):<18} "
              f"{d.get('route', {}).get('from', {}).get('city', '')} → {d.get('route', {}).get('to', {}).get('city', '')}  "
              f"{d.get('departure_time', '')}  {d.get('base_price', '')}  {d.get('status', '')}  "
              f"свободно {d.get('free_seats', '?')}")


def ask_int(prompt: str) -> int:
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("  Введите целое число.")


def build(use_mock: bool, mock_mongo: bool = False) -> TrainService:
    try:
        db = get_database(use_mock or mock_mongo)
    except Exception as error:
        raise SystemExit(f"MongoDB недоступна: {error}\nЗапустите MongoDB или используйте --mock")
    try:
        redis_client = get_redis(use_mock)
    except Exception as error:
        raise SystemExit(f"Redis недоступен: {error}\nЗапустите Redis или используйте --mock")
    repo = MongoRepository(db)
    service = TrainService(repo, RedisCache(redis_client, ttl=120))
    repo.create_indexes()
    if repo.count() == 0:
        for doc in generate():
            service.add_train(doc)
        print(f"Коллекция была пустой — добавлено {repo.count()} документов.")
    return service


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="mongomock + fakeredis вместо серверов")
    parser.add_argument("--mock-mongo", action="store_true", help="mongomock вместо MongoDB, настоящий Redis")
    args = parser.parse_args()
    service = build(args.mock, args.mock_mongo)
    repo = service.repo

    while True:
        print("\n===== MENU: ПОЕЗДА (MongoDB + Redis) =====")
        print("1. Add — добавить поезд")
        print("2. Find — найти по id (Cache-Aside)")
        print("3. List — список (skip/limit)")
        print("4. Search — запросы MongoDB")
        print("5. Update — изменить поезд")
        print("6. Delete — удалить поезд")
        print("7. Statistics — агрегации")
        print("8. Cache status")
        print("9. Clear cache")
        print("10. Benchmark MongoDB vs Redis")
        print("11. Забронировать место")
        print("12. Ближайшие отправления (Sorted Set)")
        print("0. Exit")
        choice = input("> ").strip()
        try:
            if choice == "1":
                number = input("Номер: ")
                doc = service.add_train({
                    "number": number, "name": input("Название: "), "category": input("Категория: "),
                    "base_price": float(input("Цена: ")),
                    "stops": [{"station": input("Станция отправления: "), "city": input("Город отправления: "),
                               "arrival": None, "departure": input("Отправление (2026-10-20T08:00): ")},
                              {"station": input("Станция прибытия: "), "city": input("Город прибытия: "),
                               "arrival": input("Прибытие (2026-10-20T12:00): "), "departure": None}],
                    "wagons": [{"number": 1, "type": "coupe"}, {"number": 2, "type": "sv"}],
                })
                print("Добавлен id =", doc["_id"])
            elif choice == "2":
                doc, source = service.get_train(ask_int("id: "))
                print(f"Источник: {source.upper()}")
                brief([doc])
            elif choice == "3":
                brief(repo.list_trains(ask_int("skip: "), ask_int("limit: ")))
            elif choice == "4":
                print("1 — по маршруту (вложенные поля); 2 — через город (массив); 3 — по статусу;"
                      " 4 — по цене; 5 — со свободными местами; 6 — по типу вагона; 7 — по времени отправления;"
                      " 8 — самые дешёвые (limit); 9 — отправления за дату")
                kind = input("Запрос: ").strip()
                if kind == "1":
                    brief(service.search(input("Откуда (город): "), input("Куда (город): ")))
                elif kind == "2":
                    brief(repo.through_city(input("Город: ")))
                elif kind == "3":
                    brief(repo.by_status(input("Статус: ")))
                elif kind == "4":
                    brief(repo.by_price(float(input("от: ")), float(input("до: "))))
                elif kind == "5":
                    brief(repo.with_free_seats(ask_int("Мин. свободных мест: ")))
                elif kind == "6":
                    for doc in repo.with_wagon_type(input("Тип (seated/coupe/sv): ")):
                        wagons = ", ".join(f"№{w['number']} ({w['seats'] - len(w['booked'])} своб.)" for w in doc["wagons"])
                        print(f"  {doc['number']:<6} {doc['name']:<18} вагоны: {wagons}")
                elif kind == "7":
                    brief(repo.sorted_by_departure())
                elif kind == "8":
                    brief(repo.cheapest(ask_int("Сколько: ")))
                elif kind == "9":
                    day = datetime.fromisoformat(input("Дата (2026-10-12): "))
                    brief(repo.departing_between(day, day.replace(hour=23, minute=59)))
            elif choice == "5":
                train_id = ask_int("id: ")
                field = input("Поле (name/base_price/status/category): ").strip()
                print("Изменён:")
                brief([service.update_train(train_id, {field: input("Значение: ")})])
            elif choice == "6":
                service.delete_train(ask_int("id: "))
                print("Удалён.")
            elif choice == "7":
                dump(service.statistics())
            elif choice == "8":
                dump(service.cache.stats())
                print("Активные поезда (Set):", sorted(service.cache.active_trains())[:10], "...")
                print("Последние поиски (List):", service.cache.recent_searches())
            elif choice == "9":
                print("Удалено ключей:", service.cache.clear())
            elif choice == "10":
                print(f"{'Запросов':>9} | {'MongoDB, с':>11} | {'Redis, с':>9}")
                for n, mongo, rd in service.benchmark(ask_int("id поезда: ")):
                    print(f"{n:>9} | {mongo:>11.4f} | {rd:>9.4f}")
            elif choice == "11":
                doc = service.book_seat(ask_int("id поезда: "), ask_int("Вагон: "), ask_int("Место: "))
                print("Забронировано. Свободно мест в поезде:", doc["free_seats"])
            elif choice == "12":
                for number, when in service.nearest_departures(datetime.fromisoformat(input("После (2026-10-12T00:00): "))):
                    print(f"  {number}  {when:%d.%m %H:%M}")
            elif choice == "0":
                break
            else:
                print("Неизвестный пункт.")
        except (ValidationError, ValueError, NotFoundError) as error:
            print("Ошибка:", error)


if __name__ == "__main__":
    main()
