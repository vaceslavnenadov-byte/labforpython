"""
ЛР №7. Версия 2 — после рефакторинга по SOLID.
Вариант 10. Железнодорожные перевозки.

Точка сборки (composition root): здесь выбираются конкретные реализации,
сервисы же зависят только от абстракций.
Запуск: python main.py        Тесты: python -m pytest -v
"""

from pathlib import Path

from container import Container
from infrastructure.notifier import ConsoleNotifier
from interfaces.repository import TicketRepository, TripReader
from interfaces.services import Notifier
from models.entities import Trip
from repositories.json_repository import JsonTicketRepository
from repositories.memory_repository import InMemoryTicketRepository, InMemoryTripRepository
from services.booking_service import BookingService
from services.report_service import ReportService
from services.search_service import SearchService
from ui.console import ConsoleUI


def create_trips() -> InMemoryTripRepository:
    trips = InMemoryTripRepository()
    trips.add(Trip(1, "001А", "Москва - Санкт-Петербург", "2026-10-10", 3200, 40))
    trips.add(Trip(2, "104В", "Москва - Казань", "2026-10-11", 2400, 30))
    trips.add(Trip(3, "026Ч", "Москва - Сочи", "2026-10-12", 5600, 20))
    trips.add(Trip(4, "002А", "Санкт-Петербург - Москва", "2026-10-12", 3200, 40))
    return trips


def build_container(storage_choice: str) -> Container:
    container = Container()
    container.register(TripReader, create_trips)
    if storage_choice == "2":
        path = Path(__file__).parent / "tickets.json"
        container.register(TicketRepository, lambda: JsonTicketRepository(path))
    else:
        container.register(TicketRepository, InMemoryTicketRepository)
    container.register(Notifier, ConsoleNotifier)
    container.register(SearchService, lambda: SearchService(container.resolve(TripReader)))
    container.register(BookingService, lambda: BookingService(
        container.resolve(TripReader), container.resolve(TicketRepository), container.resolve(Notifier)))
    container.register(ReportService, lambda: ReportService(
        container.resolve(TripReader), container.resolve(TicketRepository)))
    return container


def main() -> None:
    print("Выберите хранилище билетов:\n1. Память\n2. Файл (tickets.json)")
    container = build_container(input("> ").strip())
    ConsoleUI(container.resolve(SearchService), container.resolve(BookingService),
              container.resolve(ReportService)).run()


if __name__ == "__main__":
    main()
