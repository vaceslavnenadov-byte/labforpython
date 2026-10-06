"""Продажа и возврат билетов. Repository и Notifier — Mock, время — patch."""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.exceptions import NoSeatsError, NotFoundError, OperationNotAllowedError, ValidationError
from src.models.entities import TicketStatus
from src.services.ticket_service import refund_share


def test_sell_first_free_seat_and_notify(service, tickets_repo, notifier):
    tickets_repo.taken_seats.return_value = {1}
    ticket = service.sell_ticket(1, "Иванов")
    assert ticket.seat == 2 and ticket.price == 3000.0
    notifier.send.assert_called_once()
    assert notifier.send.call_args.args[0] == "Иванов"


def test_sell_specific_seat(service, tickets_repo):
    ticket = service.sell_ticket(1, "Петров", seat=3)
    saved = tickets_repo.add.call_args.args[0]
    assert ticket.seat == 3 and saved.passenger == "Петров" and saved.status == TicketStatus.SOLD


def test_cannot_sell_taken_seat(service, tickets_repo, notifier):
    tickets_repo.taken_seats.return_value = {3}
    with pytest.raises(NoSeatsError, match="занято"):
        service.sell_ticket(1, "Петров", seat=3)
    tickets_repo.add.assert_not_called()
    notifier.send.assert_not_called()


def test_no_free_seats(service, tickets_repo):
    tickets_repo.taken_seats.return_value = {1, 2, 3}
    with pytest.raises(NoSeatsError, match="нет"):
        service.sell_ticket(1, "Сидоров")


@pytest.mark.parametrize("seat", [0, 4, -1])
def test_seat_out_of_range(service, seat):
    with pytest.raises(ValidationError):
        service.sell_ticket(1, "Сидоров", seat=seat)


def test_empty_passenger(service):
    with pytest.raises(ValidationError):
        service.sell_ticket(1, "   ")


def test_cannot_sell_after_departure(service, fixed_now):
    fixed_now.return_value = datetime(2026, 10, 6)
    with pytest.raises(OperationNotAllowedError):
        service.sell_ticket(1, "Опоздавший")


@pytest.mark.parametrize("hours, share", [(72, 0.9), (24, 0.9), (23.9, 0.5), (1, 0.5), (0, 0.0), (-5, 0.0)])
def test_refund_share_rules(hours, share):
    assert refund_share(hours) == share


def test_return_ticket_early_gives_90_percent(service, tickets_repo, notifier, sold_ticket):
    tickets_repo.find_by_id.return_value = sold_ticket
    assert service.return_ticket(100) == 2700.0
    tickets_repo.update_status.assert_called_once_with(100, TicketStatus.RETURNED)
    assert "возвращён" in notifier.send.call_args.args[1]


def test_return_ticket_late_gives_half(service, tickets_repo, sold_ticket):
    tickets_repo.find_by_id.return_value = sold_ticket
    with patch("src.services.ticket_service.now", return_value=datetime(2026, 10, 5, 2, 0)):
        assert service.return_ticket(100) == 1500.0


def test_return_after_departure_forbidden(service, tickets_repo, sold_ticket, fixed_now):
    tickets_repo.find_by_id.return_value = sold_ticket
    fixed_now.return_value = datetime(2026, 10, 5, 13, 0)
    with pytest.raises(OperationNotAllowedError):
        service.return_ticket(100)
    tickets_repo.update_status.assert_not_called()


def test_return_twice_and_missing(service, tickets_repo, sold_ticket):
    sold_ticket.status = TicketStatus.RETURNED
    tickets_repo.find_by_id.return_value = sold_ticket
    with pytest.raises(OperationNotAllowedError, match="уже"):
        service.return_ticket(100)
    tickets_repo.find_by_id.return_value = None
    with pytest.raises(NotFoundError):
        service.return_ticket(5)
