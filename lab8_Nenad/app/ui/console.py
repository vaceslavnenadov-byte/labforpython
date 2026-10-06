"""Консольный интерфейс. Каждое изменяющее действие — объект-команда."""

from commands.commands import ChangeTariffCommand, CommandInvoker, RefundTicketCommand, SellTicketCommand
from factories.strategy_factory import StrategyFactory
from models.entities import DomainError
from models.enums import WagonCategory
from services.ticket_service import TicketSalesService

CATEGORIES = {"1": WagonCategory.SEATED, "2": WagonCategory.COUPE, "3": WagonCategory.SV}


class ConsoleUI:
    def __init__(self, service: TicketSalesService) -> None:
        self.service = service
        self.invoker = CommandInvoker()

    def run(self) -> None:
        while True:
            print(f"\n===== ПРОДАЖА ЖД-БИЛЕТОВ (тариф: {self.service.strategy.name}) =====")
            print("1. Поезда и цены")
            print("2. Продать билет")
            print("3. Вернуть билет")
            print("4. Сменить тариф")
            print("5. Все билеты")
            print("6. История команд")
            print("7. Отменить последнюю операцию (undo)")
            print("8. Статистика")
            print("0. Выход")
            choice = input("Выберите действие: ").strip()
            try:
                if choice == "1":
                    self.show_trains()
                elif choice == "2":
                    train = input("Номер поезда: ")
                    category = CATEGORIES.get(input("Вагон: 1 — сидячий, 2 — купе, 3 — СВ: ").strip())
                    if category is None:
                        print("Неизвестный тип вагона.")
                        continue
                    ticket = self.invoker.execute(
                        SellTicketCommand(self.service, train, category, input("Пассажир: ")))
                    print("Продан:", ticket.describe())
                elif choice == "3":
                    amount = self.invoker.execute(RefundTicketCommand(self.service, int(input("ID билета: "))))
                    print(f"К возврату: {amount:.2f} руб.")
                elif choice == "4":
                    print("Тарифы:", ", ".join(StrategyFactory.available()))
                    strategy = StrategyFactory.create(input("Тариф: ").strip())
                    print("Установлен тариф:", self.invoker.execute(ChangeTariffCommand(self.service, strategy)))
                elif choice == "5":
                    for ticket in self.service.repository.get_all():
                        print(" ", ticket.describe())
                elif choice == "6":
                    for number, name in enumerate(self.invoker.history_names(), start=1):
                        print(f"  {number}. {name}")
                elif choice == "7":
                    print(f"Отменена операция: {self.invoker.undo()}")
                elif choice == "8":
                    for key, value in self.service.statistics().items():
                        print(f"  {key}: {value}")
                elif choice == "0":
                    return
                else:
                    print("Неизвестный пункт.")
            except (DomainError, ValueError, IndexError) as error:
                print("Ошибка:", error)

    def show_trains(self) -> None:
        for train in self.service.trains.values():
            print(f"  {train.number} {train.route}, отправление {train.departure}")
            for category in train.capacity:
                occupancy = self.service.occupancy(train, category) * 100
                price = self.service.quote(train.number, category)
                print(f"      {category.value:<7} цена {price:>9.2f} руб., занято {occupancy:.0f}%")
