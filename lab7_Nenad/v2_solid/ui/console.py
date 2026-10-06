"""Консольный интерфейс — единственное место с input()/print()."""

from models.entities import CONCESSION, REGULAR, STUDENT, DomainError
from payments.methods import BonusPayment, CardPayment, CashPayment, SbpPayment
from services.booking_service import BookingService
from services.report_service import ReportService
from services.search_service import SearchService

TARIFFS = {"1": REGULAR, "2": CONCESSION, "3": STUDENT}


def read_int(prompt: str) -> int:
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("  Введите целое число.")


class ConsoleUI:
    def __init__(self, search: SearchService, booking: BookingService, reports: ReportService) -> None:
        self.search = search
        self.booking = booking
        self.reports = reports
        self.payments = {"1": CardPayment(), "2": CashPayment(), "3": SbpPayment(), "4": BonusPayment(5000)}

    def run(self) -> None:
        actions = {
            "1": ("Поиск рейса", self.search_trips),
            "2": ("Свободные места", self.show_free_seats),
            "3": ("Забронировать билет", self.book),
            "4": ("Купить (оплатить) билет", self.buy),
            "5": ("Вернуть билет", self.refund),
            "6": ("Отчёт о продажах", self.report),
        }
        while True:
            print("\n===== ЖД-БИЛЕТЫ (SOLID) =====")
            for key, (title, _) in actions.items():
                print(f"{key}. {title}")
            print("0. Выход")
            choice = input("Выберите действие: ").strip()
            if choice == "0":
                return
            if choice not in actions:
                print("Неизвестный пункт.")
                continue
            try:
                actions[choice][1]()
            except (DomainError, ValueError) as error:
                print("Ошибка:", error)

    def search_trips(self) -> None:
        city = input("Город (Enter — все): ")
        date = input("Дата ГГГГ-ММ-ДД (Enter — любая): ").strip() or None
        trips = self.search.search(city, date)
        if not trips:
            print("Рейсы не найдены.")
        for t in trips:
            print(f"  №{t.id} поезд {t.train_number} {t.route} {t.date} — {t.base_price:.2f} руб.")

    def show_free_seats(self) -> None:
        seats = self.booking.free_seats(read_int("Номер рейса: "))
        print(f"Свободно {len(seats)}: {seats[:30]}{' ...' if len(seats) > 30 else ''}")

    def book(self) -> None:
        trip_id = read_int("Номер рейса: ")
        passenger = input("Пассажир: ")
        seat = read_int("Место: ")
        tariff = TARIFFS.get(input("Тариф (1 — обычный, 2 — льготный, 3 — студенческий): ").strip(), REGULAR)
        ticket = self.booking.book(trip_id, passenger, seat, tariff)
        print(f"Билет №{ticket.id}, цена {ticket.price:.2f} руб. ({ticket.tariff.name})")

    def buy(self) -> None:
        ticket_id = read_int("Номер билета: ")
        for key, method in self.payments.items():
            print(f"  {key}. {method.name}")
        method = self.payments.get(input("Способ оплаты: ").strip())
        if method is None:
            print("Неизвестный способ оплаты.")
            return
        print(f"Списано: {self.booking.buy(ticket_id, method):.2f} руб.")

    def refund(self) -> None:
        print(f"К возврату: {self.booking.refund(read_int('Номер билета: ')):.2f} руб.")

    def report(self) -> None:
        print(f"{'Поезд':<7}{'Маршрут':<28}{'Продано':>8}{'Загрузка':>10}{'Выручка':>12}")
        for row in self.reports.sales_report():
            print(f"{row['train']:<7}{row['route']:<28}{row['sold']:>8}{row['load_percent']:>9}%{row['revenue']:>12.2f}")
