"""
ЛР №9. TCP-клиент для сервера отеля.
Запуск:  python client.py [--host 127.0.0.1] [--port 5000]
"""

import argparse
import json
import socket
import time
import uuid

from exceptions import ProtocolError
from protocol import MessageReader, encode_message, make_request

TIMEOUT = 5


class HotelClient:
    def __init__(self, host: str, port: int, timeout: float = TIMEOUT) -> None:
        self.host, self.port, self.timeout = host, port, timeout
        self.sock: socket.socket | None = None
        self.reader: MessageReader | None = None

    def connect(self) -> None:
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self.reader = MessageReader(self.sock)

    def close(self) -> None:
        if self.sock:
            self.sock.close()
            self.sock = None

    def request(self, command: str, data: dict | None = None) -> dict:
        if self.sock is None:
            self.connect()
        request_id = uuid.uuid4().hex[:8]
        self.sock.sendall(encode_message(make_request(command, data, request_id)))
        response = self.reader.read()
        if response is None:
            self.close()
            raise ConnectionError("Сервер закрыл соединение")
        if response.get("request_id") not in (request_id, None):
            raise ProtocolError("Ответ относится к другому запросу")
        return response

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()


def udp_status(host: str, port: int) -> dict | None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        udp.settimeout(2)
        udp.sendto(b"status", (host, port + 1))
        try:
            payload, _ = udp.recvfrom(4096)
            return json.loads(payload)
        except socket.timeout:
            return None


def print_rooms(rooms: list[dict]) -> None:
    if not rooms:
        print("  Номера не найдены.")
    for r in rooms:
        state = "свободен" if r["is_free"] else f"занят ({r['guest']})"
        print(f"  id={r['id']:<3} №{r['number']:<5} {r['room_type']:<7} этаж {r['floor']}  "
              f"мест {r['capacity']}  {r['price']:>9.2f} руб.  {state}")


def ask(prompt: str, cast=str, optional: bool = False):
    while True:
        text = input(prompt).strip()
        if optional and not text:
            return None
        try:
            return cast(text)
        except ValueError:
            print("  Некорректное значение.")


def room_form(optional: bool) -> dict:
    fields = {"number": str, "room_type": str, "floor": int, "price": float, "capacity": int}
    data = {}
    hint = " (Enter — не менять)" if optional else ""
    for name, cast in fields.items():
        value = ask(f"  {name}{hint}: ", cast, optional)
        if value is not None:
            data[name] = value
    return data


MENU = """
=== HOTEL CLIENT ===
1. Получить список номеров
2. Получить номер
3. Создать номер
4. Изменить номер
5. Удалить номер
6. Поиск свободных номеров (спец. операция)
7. Заселить гостя
8. Выселить гостя
9. Статистика
10. Ping (время отклика)
11. История запросов сервера
12. Статус через UDP
13. Демонстрация тайм-аута
14. Остановить сервер (admin)
0. Выход"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    client = HotelClient(args.host, args.port)
    try:
        client.connect()
    except OSError as exc:
        print(f"Сервер {args.host}:{args.port} недоступен: {exc}")
        return

    while True:
        print(MENU)
        choice = input("Введите команду: ").strip()
        if choice == "0":
            break
        try:
            if choice == "1":
                response = client.request("list")
            elif choice == "2":
                response = client.request("get", {"id": ask("id: ", int)})
            elif choice == "3":
                response = client.request("create", room_form(optional=False))
            elif choice == "4":
                room_id = ask("id: ", int)
                response = client.request("update", {"id": room_id, **room_form(optional=True)})
            elif choice == "5":
                response = client.request("delete", {"id": ask("id: ", int)})
            elif choice == "6":
                data = {k: v for k, v in {
                    "room_type": ask("Тип (single/double/suite, Enter — любой): ", str, True),
                    "min_capacity": ask("Мин. вместимость (Enter — 1): ", int, True),
                    "max_price": ask("Макс. цена (Enter — любая): ", float, True),
                }.items() if v is not None}
                response = client.request("find_free", data)
            elif choice == "7":
                response = client.request("check_in", {"id": ask("id: ", int), "guest": input("Гость: ")})
            elif choice == "8":
                response = client.request("check_out", {"id": ask("id: ", int)})
            elif choice == "9":
                response = client.request("stats")
            elif choice == "10":
                start = time.perf_counter()
                response = client.request("ping")
                print(f"RTT: {(time.perf_counter() - start) * 1000:.2f} мс")
            elif choice == "11":
                response = client.request("history")
            elif choice == "12":
                status = udp_status(args.host, args.port)
                print("UDP-ответ:", status if status else "не получен (UDP не гарантирует доставку)")
                continue
            elif choice == "13":
                print(f"Сервер будет «думать» 7 с, тайм-аут клиента {TIMEOUT} с...")
                response = client.request("sleep", {"seconds": 7})
            elif choice == "14":
                response = client.request("shutdown", {"token": input("Токен администратора: ")})
            else:
                print("Неизвестная команда.")
                continue
        except socket.timeout:
            print("Ошибка: тайм-аут ожидания ответа сервера. Соединение будет переустановлено.")
            client.close()
            continue
        except (ConnectionError, OSError) as exc:
            print("Ошибка соединения:", exc)
            client.close()
            continue
        except ProtocolError as exc:
            print("Ошибка протокола:", exc)
            continue

        if response["status"] == "error":
            print("Ошибка сервера:", response["error"])
        elif isinstance(response["data"], list) and response["data"] and "number" in response["data"][0]:
            print_rooms(response["data"])
        elif isinstance(response["data"], dict) and "number" in response["data"]:
            print_rooms([response["data"]])
        else:
            print(json.dumps(response["data"], ensure_ascii=False, indent=2))
    client.close()


if __name__ == "__main__":
    main()
