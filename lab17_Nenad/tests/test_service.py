import pytest

from database.models import TicketStatus, WagonType
from services.railway_service import BookingError
from tests.conftest import ADMIN_ID


async def test_search_and_schedule(service):
    trains = await service.search("Москва", "Санкт-Петербург")
    assert {t.number for t in trains} == {"001А", "752А"}
    assert len(await service.schedule()) == 8
    assert "Казань" in await service.cities()


async def test_book_view_rename_return(service):
    user = await service.register_user(42, "Иван Тестов", "ivan")
    ticket = await service.book(user, 1, WagonType.SV, 5, "Тестов Иван")
    assert ticket.price == 9600 and ticket.train.number == "001А"
    assert [t.id for t in await service.user_tickets(user)] == [ticket.id]
    assert (await service.rename_passenger(user, ticket.id, "Петров Пётр")).passenger_name == "Петров Пётр"
    assert await service.return_ticket(user, ticket.id) == 8640.0
    assert (await service.get_own_ticket(user, ticket.id)).status == TicketStatus.RETURNED
    with pytest.raises(BookingError):
        await service.return_ticket(user, ticket.id)


async def test_seat_cannot_be_sold_twice(service):
    user = await service.register_user(42, "Иван", None)
    await service.book(user, 1, WagonType.COUPE, 10, "Иванов Иван")
    with pytest.raises(BookingError, match="занято"):
        await service.book(user, 1, WagonType.COUPE, 10, "Петров Пётр")
    assert 10 not in await service.free_seats(1, WagonType.COUPE)


async def test_foreign_ticket_is_hidden_but_admin_sees_it(service):
    owner = await service.register_user(42, "Иван", None)
    ticket = await service.book(owner, 2, WagonType.SEATED, 30, "Иванов Иван")
    stranger = await service.register_user(43, "Чужой", None)
    with pytest.raises(BookingError):
        await service.get_own_ticket(stranger, ticket.id)
    admin = await service.register_user(ADMIN_ID, "Админ", None)
    assert admin.is_admin and (await service.get_own_ticket(admin, ticket.id)).id == ticket.id


async def test_available_types_and_statistics(service):
    options = {t for t, _, _ in await service.available_types(1)}
    assert options == {WagonType.COUPE, WagonType.SV}               # у «Красной стрелы» нет сидячих
    stats = await service.statistics()
    assert stats["trains"] == 16 and stats["active"] == 12 and stats["stations"] == 10
