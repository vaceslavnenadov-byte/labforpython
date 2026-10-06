"""
ЛР №8. Паттерны проектирования.
Вариант 10. Железнодорожные перевозки — система продажи билетов.

Паттерны: Repository, Factory (TicketFactory, StrategyFactory), Strategy (тарифы), Command (+ история и undo).
Запуск: python main.py          Тесты: python -m pytest -v
"""

from datetime import date, timedelta
from pathlib import Path

from factories.strategy_factory import StrategyFactory
from models.entities import Train
from models.enums import WagonCategory
from repositories.file_repository import FileTicketRepository
from repositories.memory_repository import InMemoryTicketRepository
from services.ticket_service import TicketSalesService
from ui.console import ConsoleUI


def create_trains() -> list[Train]:
    today = date.today()
    return [
        Train("001А", "Москва - Санкт-Петербург", today + timedelta(days=2), 2500,
              {WagonCategory.SEATED: 60, WagonCategory.COUPE: 36, WagonCategory.SV: 4}),
        Train("104В", "Москва - Казань", today + timedelta(days=20), 1800,
              {WagonCategory.COUPE: 36, WagonCategory.SV: 18}),
        Train("026Ч", "Москва - Сочи", today + timedelta(days=60), 3900,
              {WagonCategory.COUPE: 72, WagonCategory.SV: 18}),
    ]


def main() -> None:
    print("Выберите хранилище:\n1. Память\n2. Файл")
    if input("> ").strip() == "2":
        repository = FileTicketRepository(Path(__file__).parent / "tickets.json")
    else:
        repository = InMemoryTicketRepository()
    service = TicketSalesService(repository, StrategyFactory.create("standard"), create_trains())
    ConsoleUI(service).run()


if __name__ == "__main__":
    main()
