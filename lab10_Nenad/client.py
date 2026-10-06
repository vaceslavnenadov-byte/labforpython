"""
ЛР №10. HTTP-клиент (requests) для REST API поездов.
Запуск: python client.py [--url http://127.0.0.1:5000] [--key secret-key]
"""

import argparse
import json

import requests

FIELDS = [("number", str), ("departure_station", str), ("arrival_station", str),
          ("departure_time", str), ("arrival_time", str), ("wagons", int),
          ("seats_per_wagon", int), ("booked_seats", int), ("price", float)]


class TrainApiClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "X-API-Key": api_key,
                                     "X-Client-Version": "1.0"})

    def call(self, method: str, path: str, **kwargs) -> requests.Response:
        return self.session.request(method, self.base_url + path, timeout=5, **kwargs)


def ask_fields(optional: bool) -> dict:
    data = {}
    for name, cast in FIELDS:
        text = input(f"  {name}{' (Enter — пропустить)' if optional else ''}: ").strip()
        if optional and not text:
            continue
        try:
            data[name] = cast(text)
        except ValueError:
            data[name] = text  # пусть сервер вернёт 400 — демонстрация валидации
    return data


def show(response: requests.Response) -> None:
    print(f"HTTP {response.status_code} {response.reason}")
    if response.content:
        data = response.json()
        if isinstance(data, list) and data and "route" in data[0]:
            for t in data:
                print(f"  id={t['id']:<3} {t['number']:<6} {t['route']:<32} {t['departure_time']}  "
                      f"{t['price']:>8.2f} руб.  свободно {t['free_seats']}/{t['total_seats']}")
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))


MENU = """
=========================
REST CLIENT — ПОЕЗДА
=========================
1. Получить список
2. Получить объект
3. Создать
4. Изменить (PUT)
5. Частично изменить (PATCH)
6. Удалить
7. Фильтрация
8. Сортировка
9. Свободные места (спец. операция)
10. Купить места
11. Пагинация
0. Выход"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5000")
    parser.add_argument("--key", default="secret-key")
    args = parser.parse_args()
    client = TrainApiClient(args.url, args.key)

    while True:
        print(MENU)
        choice = input("Выберите действие: ").strip()
        try:
            if choice == "1":
                show(client.call("GET", "/trains"))
            elif choice == "2":
                show(client.call("GET", f"/trains/{input('id: ')}"))
            elif choice == "3":
                show(client.call("POST", "/trains", json=ask_fields(False)))
            elif choice == "4":
                train_id = input("id: ")
                show(client.call("PUT", f"/trains/{train_id}", json=ask_fields(False)))
            elif choice == "5":
                train_id = input("id: ")
                show(client.call("PATCH", f"/trains/{train_id}", json=ask_fields(True)))
            elif choice == "6":
                show(client.call("DELETE", f"/trains/{input('id: ')}"))
            elif choice == "7":
                params = {k: v for k, v in {
                    "from": input("Откуда (Enter — любой): ").strip(),
                    "to": input("Куда (Enter — любой): ").strip(),
                    "max_price": input("Макс. цена (Enter — любая): ").strip(),
                }.items() if v}
                show(client.call("GET", "/trains", params=params))
            elif choice == "8":
                params = {"sort": input("Поле (price/departure_time/free_seats/number): ").strip(),
                          "order": input("Порядок (asc/desc): ").strip() or "asc"}
                show(client.call("GET", "/trains", params=params))
            elif choice == "9":
                show(client.call("GET", "/trains/free-seats",
                                 params={"min_seats": input("Минимум свободных мест: ").strip() or "1"}))
            elif choice == "10":
                train_id = input("id: ")
                try:
                    count = int(input("Количество мест: "))
                except ValueError:
                    print("Введите целое число.")
                    continue
                show(client.call("POST", f"/trains/{train_id}/bookings", json={"count": count}))
            elif choice == "11":
                show(client.call("GET", "/trains", params={"page": input("page: "), "limit": input("limit: ")}))
            elif choice == "0":
                break
            else:
                print("Неизвестный пункт.")
        except requests.ConnectionError:
            print(f"Сервер {args.url} недоступен.")
        except requests.Timeout:
            print("Тайм-аут запроса.")


if __name__ == "__main__":
    main()
