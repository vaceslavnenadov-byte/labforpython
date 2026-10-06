from datetime import date, timedelta

import pytest

from commands.commands import ChangeTariffCommand, CommandInvoker, RefundTicketCommand, SellTicketCommand
from factories.strategy_factory import StrategyFactory
from factories.ticket_factory import TicketFactory
from interfaces.strategies import PricingContext
from models.entities import CoupeTicket, DomainError, SeatedTicket, SvTicket, Train
from models.enums import TicketStatus, WagonCategory
from repositories.file_repository import FileTicketRepository
from repositories.memory_repository import InMemoryTicketRepository
from services.ticket_service import TicketSalesService
from strategies.pricing import ConcessionPricing, DynamicPricing, StandardPricing

TODAY = date(2026, 10, 1)


@pytest.fixture
def service():
    trains = [Train("001А", "Москва - Санкт-Петербург", TODAY + timedelta(days=10), 1000,
                    {WagonCategory.SEATED: 2, WagonCategory.COUPE: 4, WagonCategory.SV: 1})]
    return TicketSalesService(InMemoryTicketRepository(), StandardPricing(), trains, TODAY)


# ---------- Factory ----------
@pytest.mark.parametrize("category, cls", [
    ("seated", SeatedTicket), ("coupe", CoupeTicket), ("sv", SvTicket),
    (WagonCategory.SV, SvTicket),
])
def test_factory_creates_right_ticket_type(category, cls):
    assert type(TicketFactory.create(category, 1, "001А", "Иванов", 1)) is cls


def test_factory_rejects_unknown_type():
    with pytest.raises(ValueError):
        TicketFactory.create("plackart", 1, "001А", "Иванов", 1)


def test_strategy_factory():
    assert isinstance(StrategyFactory.create("dynamic"), DynamicPricing)
    with pytest.raises(ValueError):
        StrategyFactory.create("vip")


# ---------- Strategy ----------
def test_strategy_changes_price(service):
    standard = service.quote("001А", WagonCategory.COUPE)
    service.set_strategy(ConcessionPricing())
    concession = service.quote("001А", WagonCategory.COUPE)
    assert standard == 1800 and concession == 900


def test_dynamic_pricing_depends_on_context():
    strategy = DynamicPricing()
    assert strategy.calculate(1000, 1.0, PricingContext(0.0, 60)) == 850       # ранняя покупка
    assert strategy.calculate(1000, 1.0, PricingContext(1.0, 1)) == 1800       # полный поезд + скоро
    assert strategy.calculate(1000, 1.0, PricingContext(0.5, 10)) == 1250


# ---------- Repository ----------
def test_memory_repository_crud():
    repo = InMemoryTicketRepository()
    ticket = TicketFactory.create("sv", repo.next_id(), "001А", "Иванов", 1)
    repo.add(ticket)
    assert repo.get(1) is ticket and repo.next_id() == 2
    repo.delete(1)
    assert repo.get_all() == []


def test_file_repository_persists(tmp_path, service):
    path = tmp_path / "t.json"
    service.repository = FileTicketRepository(path)
    sold = service.sell("001А", "coupe", "Иванов")
    restored = FileTicketRepository(path).get(sold.id)
    assert isinstance(restored, CoupeTicket) and restored.price == 1800


# ---------- Основная бизнес-операция ----------
def test_sell_assigns_free_seats_until_full(service):
    first = service.sell("001А", "seated", "А")
    second = service.sell("001А", "seated", "Б")
    assert (first.seat, second.seat) == (1, 2)
    with pytest.raises(DomainError, match="нет свободных мест"):
        service.sell("001А", "seated", "В")


def test_refund_returns_90_percent_and_frees_seat(service):
    ticket = service.sell("001А", "sv", "Иванов")
    assert service.refund(ticket.id) == 2700
    assert service.sell("001А", "sv", "Петров").seat == 1


# ---------- Command ----------
def test_command_history_and_undo(service):
    invoker = CommandInvoker()
    ticket = invoker.execute(SellTicketCommand(service, "001А", "coupe", "Иванов"))
    invoker.execute(RefundTicketCommand(service, ticket.id))
    invoker.execute(ChangeTariffCommand(service, ConcessionPricing()))
    assert invoker.history_names() == ["SellTicket", "RefundTicket", "ChangeTariff"]

    assert invoker.undo() == "ChangeTariff" and service.strategy.name == "стандартный"
    assert invoker.undo() == "RefundTicket" and ticket.status == TicketStatus.SOLD
    assert invoker.undo() == "SellTicket" and service.repository.get_all() == []
    with pytest.raises(IndexError):
        invoker.undo()


def test_failed_command_not_added_to_history(service):
    invoker = CommandInvoker()
    with pytest.raises(DomainError):
        invoker.execute(SellTicketCommand(service, "999", "sv", "Иванов"))
    assert invoker.history_names() == []
