import pytest

from exceptions import ConflictError, TrainNotFoundError, ValidationError
from repository import TrainRepository
from service import TrainService, seed


@pytest.fixture
def service():
    s = TrainService(TrainRepository())
    seed(s)
    return s


def test_filter_and_sort(service):
    trains = service.get_trains({"from": "москва", "to": "петербург"}, sort="price", order="desc")
    assert [t.number for t in trains] == ["752А", "001А"]


def test_free_seats_operation(service):
    result = service.trains_with_free_seats(min_seats=100)
    assert "026Ч" not in [t["number"] for t in result]          # 576 из 576 занято
    assert all(t["free_seats"] >= 100 for t in result)


def test_book_seats_conflict(service):
    with pytest.raises(ConflictError):
        service.book_seats(4, 1)                                  # 026Ч заполнен
    assert service.book_seats(1, 2).booked_seats == 402


def test_validation_errors(service):
    with pytest.raises(ValidationError):
        service.patch_train(1, {"arrival_time": "2026-10-01T00:00"})   # прибытие раньше отправления
    with pytest.raises(ValidationError):
        service.patch_train(1, {"price": -1})


def test_delete_rules(service):
    with pytest.raises(ConflictError):
        service.delete_train(1)                  # есть проданные места
    service.patch_train(1, {"status": "cancelled"})
    service.delete_train(1)
    with pytest.raises(TrainNotFoundError):
        service.get_train(1)
