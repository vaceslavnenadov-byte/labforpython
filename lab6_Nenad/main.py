"""
Лабораторная работа №6. Декораторы, контекстные менеджеры и расширенные возможности Python.
Вариант 10. Железнодорожные перевозки (поезд, вагон, билет).

Меню формируется автоматически: методы ConsoleUI помечены декоратором @command
и обнаруживаются через inspect.getmembers().
"""

import inspect
from pathlib import Path

from context import OperationLogger, Transaction, measure
from decorators import command, log_call, retry, timing
from exceptions import RailwayError
from introspection import inspect_object, safe_set
from models import Ticket, TicketStatus, Train, WagonType
from protocols import Reportable, print_report
from services import RailwayService

LOG_FILE = Path(__file__).parent / "operations.log"


def read_int(prompt: str) -> int:
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("  Ошибка: введите целое число.")


def read_float(prompt: str) -> float:
    while True:
        try:
            return float(input(prompt).replace(",", "."))
        except ValueError:
            print("  Ошибка: введите число.")


def fill_demo(service: RailwayService) -> None:
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):  # не засоряем вывод логами при старте
        t1 = service.add_train("001А", "Москва - Санкт-Петербург", "2026-10-10 23:55", 2500,
                               [WagonType.SEATED, WagonType.COUPE, WagonType.SV])
        t2 = service.add_train("104В", "Москва - Казань", "2026-10-11 21:20", 1800,
                               [WagonType.COUPE, WagonType.COUPE])
        service.add_train("026Ч", "Москва - Сочи", "2026-10-12 12:00", 4100, [WagonType.SV])
        service.pay_ticket(service.book_ticket(t1.id, 2, 5, "Иванов И.И.").id)
        service.book_ticket(t1.id, 2, 6, "Петрова А.С.")
        service.book_ticket(t1.id, 3, 1, "Сидоров П.П.")
        service.pay_ticket(service.book_ticket(t2.id, 1, 10, "Кузнецова М.В.").id)


class ConsoleUI:
    def __init__(self, service: RailwayService):
        self.service = service

    # ----- автоматическое построение меню -----
    def commands(self):
        found = [m for _, m in inspect.getmembers(self, inspect.ismethod) if hasattr(m, "menu_title")]
        return sorted(found, key=lambda m: m.menu_order)

    def run(self):
        while True:
            menu = self.commands()
            print("\n===== ЖЕЛЕЗНОДОРОЖНЫЕ ПЕРЕВОЗКИ =====")
            for index, method in enumerate(menu, start=1):
                print(f"{index}. {method.menu_title}")
            print("0. Выход")
            choice = input("Выберите действие: ").strip()
            if choice == "0":
                break
            if not choice.isdigit() or not 1 <= int(choice) <= len(menu):
                print("Неизвестный пункт меню.")
                continue
            method = menu[int(choice) - 1]
            try:
                with OperationLogger(method.__name__, LOG_FILE):
                    method()
            except RailwayError as error:
                print(f"Ошибка ({type(error).__name__}): {error}")
            except ZeroDivisionError as error:
                print("Ошибка вычисления:", error)

    # ----- пункты меню -----
    @command("Добавить поезд", 1)
    def add_train(self):
        number = input("Номер поезда: ").strip()
        route = input("Маршрут: ")
        departure = input("Отправление (ГГГГ-ММ-ДД ЧЧ:ММ): ")
        price = read_float("Базовая цена (сидячий вагон): ")
        print("Типы вагонов: 1 — сидячий, 2 — купе, 3 — СВ. Пример: 1 2 2 3")
        mapping = {"1": WagonType.SEATED, "2": WagonType.COUPE, "3": WagonType.SV}
        codes = input("Состав: ").split()
        wagons = [mapping[c] for c in codes if c in mapping]
        print("Создан:", self.service.add_train(number, route, departure, price, wagons).get_report_data())

    @command("Удалить поезд", 2)
    def delete_train(self):
        self.service.delete_train(read_int("ID поезда: "))
        print("Поезд удалён.")

    @command("Найти поезд", 3)
    def find_train(self):
        for train in self.service.find_trains(input("Номер или город: ")) or []:
            print(f"  id={train.id}", train.get_report_data())

    @command("Показать все поезда и билеты", 4)
    def show_all(self):
        for train in self.service.trains:
            print(f"  id={train.id}", train.get_report_data())
            for wagon in train.wagons:
                print(f"      {wagon.get_report_data()}, цена {train.seat_price(wagon):.2f}")
        print("Билеты:")
        for ticket in self.service.tickets:
            print("  ", ticket.get_report_data())

    @command("Забронировать билет", 5)
    def book(self):
        ticket = self.service.book_ticket(read_int("ID поезда: "), read_int("Вагон №: "),
                                          read_int("Место: "), input("Пассажир: "))
        print("Забронирован:", ticket.get_report_data())

    @command("Изменить статус билета (оплатить/использовать/вернуть)", 6)
    def change_status(self):
        ticket_id = read_int("ID билета: ")
        action = input("1 — оплатить, 2 — использовать, 3 — вернуть: ").strip()
        if action == "1":
            self.service.pay_ticket(ticket_id)
        elif action == "2":
            self.service.use_ticket(ticket_id)
        elif action == "3":
            print(f"К возврату: {self.service.return_ticket(ticket_id):.2f} руб.")
        else:
            print("Неизвестное действие.")
            return
        print("Статус:", self.service.get_ticket(ticket_id).status.value)

    @command("Загрузка поезда", 7)
    def load(self):
        print(f"Загрузка: {self.service.train_load(read_int('ID поезда: '))}%")

    @command("Поиск свободных мест", 8)
    def free(self):
        train_id = read_int("ID поезда: ")
        kind = input("Тип вагона (1 — сидячий, 2 — купе, 3 — СВ, Enter — любой): ").strip()
        wagon_type = {"1": WagonType.SEATED, "2": WagonType.COUPE, "3": WagonType.SV}.get(kind)
        result = self.service.free_seats(train_id, wagon_type)
        if not result:
            print("Свободных мест нет.")
        for wagon, seats in result.items():
            preview = ", ".join(map(str, seats[:15])) + (" ..." if len(seats) > 15 else "")
            print(f"  Вагон №{wagon}: {len(seats)} мест — {preview}")

    @command("Статистика", 9)
    def stats(self):
        for key, value in self.service.statistics().items():
            print(f"  {key}: {value}")

    @command("Интроспекция объекта", 10)
    def introspect(self):
        kind = input("1 — поезд, 2 — билет: ").strip()
        obj = self.service.get_train(read_int("ID: ")) if kind == "1" else self.service.get_ticket(read_int("ID: "))
        inspect_object(obj)
        print("Сигнатура book_ticket:", inspect.signature(RailwayService.book_ticket))
        print("Имя сохранено благодаря @wraps:", RailwayService.book_ticket.__name__)

    @command("Демонстрация декораторов", 11)
    def demo_decorators(self):
        @log_call
        @timing
        def ticket_price(train: Train, wagon_number: int) -> float:
            return train.seat_price(train.find_wagon(wagon_number))

        ticket_price(self.service.trains[0], 2)

        attempts = {"count": 0}

        @retry(3, exceptions=(ConnectionError,))
        def unstable_payment_gateway() -> str:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise ConnectionError("платёжный шлюз не отвечает")
            return "оплата подтверждена"

        print("Результат:", unstable_payment_gateway())

        print("@require_status: пробуем использовать неоплаченный билет")
        booked = next((t for t in self.service.tickets if t.status == TicketStatus.BOOKED), None)
        if booked:
            try:
                booked.use()
            except RailwayError as error:
                print("  ", error)

    @command("Демонстрация контекстных менеджеров", 12)
    def demo_context(self):
        train = self.service.trains[0]
        print(f"Групповое бронирование 3 мест в вагоне 3 поезда {train.number} (место 1 уже занято):")
        before = len(self.service.tickets)
        try:
            with Transaction(self.service) as service, measure("групповое бронирование"):
                for seat in (2, 3, 1):
                    service.book_ticket(train.id, 3, seat, f"Группа, место {seat}")
        except RailwayError as error:
            print("Бронирование отменено целиком:", error)
        print(f"Билетов до: {before}, после: {len(self.service.tickets)}")
        print(f"Журнал операций OperationLogger: {LOG_FILE.name}")

    @command("Демонстрация Protocol и setattr", 13)
    def demo_protocol(self):
        items: list[Reportable] = [self.service.trains[0], self.service.trains[0].wagons[0]]
        if self.service.tickets:
            items.append(self.service.tickets[0])
        for item in items:
            print(f"{type(item).__name__} соответствует Reportable:", isinstance(item, Reportable))
            print_report(item)
        ticket: Ticket = self.service.tickets[0]
        print("setattr passenger:", safe_set(ticket, "passenger", ticket.passenger.upper()), ticket.passenger)
        print("setattr unknown:", safe_set(ticket, "unknown_field", 1))


def main():
    service = RailwayService()
    fill_demo(service)
    ConsoleUI(service).run()


if __name__ == "__main__":
    main()
