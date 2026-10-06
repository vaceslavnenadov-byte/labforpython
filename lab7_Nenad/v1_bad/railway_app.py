"""
ЛР №7. Версия 1 — РАБОТАЮЩАЯ, НО С НАМЕРЕННЫМИ НАРУШЕНИЯМИ SOLID.
Вариант 10. Железнодорожные перевозки: поиск рейса, бронирование, покупка, возврат.

Нарушения отмечены комментариями  # [НАРУШЕНИЕ ...].
Запуск: python railway_app.py
"""

import json
from datetime import datetime


class Trip:
    def __init__(self, trip_id, train_number, route, date, price, seats):
        self.trip_id = trip_id
        self.train_number = train_number
        self.route = route
        self.date = date
        self.price = price
        self.seats = seats


class Ticket:
    def __init__(self, ticket_id, trip_id, passenger, seat, price):
        self.ticket_id = ticket_id
        self.trip_id = trip_id
        self.passenger = passenger
        self.seat = seat
        self.price = price
        self.status = "booked"


# [НАРУШЕНИЕ ISP] «Толстый» интерфейс: каждый вид билета обязан реализовать всё.
class TicketOperations:
    def book(self): raise NotImplementedError
    def pay(self): raise NotImplementedError
    def refund(self): raise NotImplementedError
    def print_ticket(self): raise NotImplementedError
    def send_sms(self): raise NotImplementedError
    def export_to_xml(self): raise NotImplementedError


class PaperTicket(Ticket, TicketOperations):
    def book(self): self.status = "booked"
    def pay(self): self.status = "paid"
    def refund(self): self.status = "refunded"
    def print_ticket(self): print(f"Печать билета {self.ticket_id}")
    def send_sms(self): raise NotImplementedError("Бумажный билет не отправляется по SMS")
    def export_to_xml(self): raise NotImplementedError("Не поддерживается")


# [НАРУШЕНИЕ LSP] Льготный билет нельзя вернуть, хотя базовый класс это обещает.
class ConcessionTicket(PaperTicket):
    def refund(self):
        raise Exception("Льготные билеты возврату не подлежат!")


class FileStorage:
    """Хранение в JSON-файле."""

    def save(self, trips, tickets):
        with open("railway_v1.json", "w", encoding="utf-8") as file:
            json.dump({"trips": [t.__dict__ for t in trips], "tickets": [t.__dict__ for t in tickets]},
                      file, ensure_ascii=False)


# [НАРУШЕНИЕ SRP] Один класс: данные, поиск, бронирование, оплата, уведомления,
#                  отчёты, хранение и работа с консолью.
class RailwayManager:
    def __init__(self):
        self.trips = []
        self.tickets = []
        self.storage = FileStorage()   # [НАРУШЕНИЕ DIP] жёстко созданная зависимость
        self.next_ticket_id = 1

    def add_trip(self, trip):
        self.trips.append(trip)

    def search_trips(self, city):
        result = [t for t in self.trips if city.lower() in t.route.lower()]
        for trip in result:  # [НАРУШЕНИЕ SRP] вывод в консоль внутри бизнес-логики
            print(f"{trip.trip_id}: {trip.train_number} {trip.route} {trip.date} {trip.price} руб.")
        return result

    def book(self, trip_id, passenger, seat, concession=False):
        trip = next(t for t in self.trips if t.trip_id == trip_id)
        if seat < 1 or seat > trip.seats:
            print("Нет такого места")
            return None
        for ticket in self.tickets:
            if ticket.trip_id == trip_id and ticket.seat == seat and ticket.status != "refunded":
                print("Место занято")
                return None
        cls = ConcessionTicket if concession else PaperTicket
        price = trip.price * 0.5 if concession else trip.price
        ticket = cls(self.next_ticket_id, trip_id, passenger, seat, price)
        self.next_ticket_id += 1
        self.tickets.append(ticket)
        self.storage.save(self.trips, self.tickets)
        print(f"[EMAIL] {passenger}: билет №{ticket.ticket_id} забронирован")  # [НАРУШЕНИЕ SRP]
        return ticket

    # [НАРУШЕНИЕ OCP] Новый способ оплаты = изменение этого метода.
    def buy(self, ticket_id, payment_type):
        ticket = next(t for t in self.tickets if t.ticket_id == ticket_id)
        if payment_type == "card":
            commission = ticket.price * 0.015
            print(f"Оплата картой: {ticket.price + commission:.2f} (комиссия 1.5%)")
        elif payment_type == "cash":
            print(f"Оплата наличными в кассе: {ticket.price:.2f}")
        elif payment_type == "sbp":
            print(f"Оплата через СБП: {ticket.price:.2f}")
        else:
            print("Неизвестный способ оплаты")
            return False
        ticket.pay()
        self.storage.save(self.trips, self.tickets)
        print(f"[EMAIL] {ticket.passenger}: билет №{ticket.ticket_id} оплачен")
        return True

    def refund(self, ticket_id):
        ticket = next(t for t in self.tickets if t.ticket_id == ticket_id)
        ticket.refund()  # для ConcessionTicket — неожиданное исключение (LSP)
        self.storage.save(self.trips, self.tickets)
        print(f"[EMAIL] {ticket.passenger}: билет №{ticket.ticket_id} возвращён")

    def report(self):
        print(f"=== Отчёт {datetime.now():%d.%m.%Y} ===")
        for trip in self.trips:
            sold = [t for t in self.tickets if t.trip_id == trip.trip_id and t.status == "paid"]
            print(f"{trip.train_number}: продано {len(sold)}, выручка {sum(t.price for t in sold):.2f}")


if __name__ == "__main__":
    manager = RailwayManager()
    manager.add_trip(Trip(1, "001А", "Москва - Санкт-Петербург", "2026-10-10", 3000, 50))
    manager.add_trip(Trip(2, "104В", "Москва - Казань", "2026-10-11", 2200, 40))
    manager.search_trips("Москва")
    t1 = manager.book(1, "Иванов", 5)
    t2 = manager.book(1, "Петров", 5)            # место занято
    t3 = manager.book(2, "Сидорова", 1, concession=True)
    manager.buy(t1.ticket_id, "card")
    manager.buy(t3.ticket_id, "cash")
    manager.report()
    try:
        manager.refund(t3.ticket_id)             # нарушение LSP проявляется здесь
    except Exception as error:
        print("Сбой при возврате:", error)
