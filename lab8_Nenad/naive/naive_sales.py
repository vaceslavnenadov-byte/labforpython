"""
ЛР №8. Этап 1 — НАИВНАЯ РЕАЛИЗАЦИЯ (без паттернов).
Вариант 10. Продажа железнодорожных билетов.

Проблемы (см. README):
* создание билетов через if/elif по типу вагона          → Factory;
* выбор тарифа через if/elif                              → Strategy;
* обработка команд меню через if/elif, нет истории/отмены → Command;
* данные хранятся прямо внутри сервиса в списке           → Repository.
"""


class TicketOffice:
    def __init__(self):
        self.tickets = []          # хранение данных внутри сервиса
        self.next_id = 1

    def calculate_price(self, base, wagon, tariff, occupancy=0.0, days_before=30):
        if wagon == "seated":
            price = base
        elif wagon == "coupe":
            price = base * 1.8
        elif wagon == "sv":
            price = base * 3.0
        else:
            raise ValueError("Неизвестный тип вагона")
        if tariff == "standard":
            pass
        elif tariff == "concession":
            price *= 0.5
        elif tariff == "dynamic":
            price *= 1 + occupancy * 0.5
            if days_before < 3:
                price *= 1.2
        else:
            raise ValueError("Неизвестный тариф")
        return round(price, 2)

    def sell(self, passenger, wagon, tariff, base=2000):
        if wagon == "seated":
            ticket = {"type": "Сидячий", "services": "-"}
        elif wagon == "coupe":
            ticket = {"type": "Купе", "services": "бельё"}
        elif wagon == "sv":
            ticket = {"type": "СВ", "services": "бельё, питание"}
        else:
            raise ValueError("Неизвестный тип вагона")
        ticket.update(id=self.next_id, passenger=passenger, status="sold",
                      price=self.calculate_price(base, wagon, tariff))
        self.next_id += 1
        self.tickets.append(ticket)
        return ticket


def main():
    office = TicketOffice()
    while True:
        command = input("Команда (sell / refund / list / exit): ").strip()
        if command == "sell":
            ticket = office.sell(input("Пассажир: "), input("Вагон (seated/coupe/sv): "),
                                 input("Тариф (standard/concession/dynamic): "))
            print(ticket)
        elif command == "refund":
            ticket_id = int(input("ID: "))
            for t in office.tickets:
                if t["id"] == ticket_id:
                    t["status"] = "refunded"
        elif command == "list":
            for t in office.tickets:
                print(t)
        elif command == "exit":
            break
        # отменить последнюю операцию невозможно — истории нет


if __name__ == "__main__":
    main()
