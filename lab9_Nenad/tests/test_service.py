import pytest

from exceptions import ConflictError, RoomNotFoundError, ValidationError
from repository import RoomRepository
from service import RoomService, seed


@pytest.fixture
def service():
    s = RoomService(RoomRepository())
    seed(s)
    return s


def test_create_room_validates(service):
    with pytest.raises(ValidationError):
        service.create_room({"number": "401", "room_type": "single", "floor": 4, "price": -5, "capacity": 1})
    with pytest.raises(ValidationError, match="missing"):
        service.create_room({"number": "401"})
    with pytest.raises(ConflictError):
        service.create_room({"number": "101", "room_type": "single", "floor": 1, "price": 1, "capacity": 1})


def test_find_free_rooms_filters(service):
    rooms = service.find_free_rooms("double", min_capacity=3)
    assert [r.number for r in rooms] == ["202"]
    assert all(r.is_free for r in service.find_free_rooms())
    assert service.find_free_rooms(max_price=100) == []


def test_check_in_and_out(service):
    room = service.check_in(1, "Петров")
    assert not room.is_free and room.guest == "Петров"
    with pytest.raises(ConflictError):
        service.check_in(1, "Сидоров")
    assert service.check_out(1).is_free


def test_update_and_delete(service):
    assert service.update_room(2, {"price": 3500}).price == 3500
    with pytest.raises(ConflictError):
        service.delete_room(3)          # номер занят
    service.delete_room(2)
    with pytest.raises(RoomNotFoundError):
        service.get_room(2)


def test_statistics(service):
    stats = service.statistics()
    assert stats["total"] == 6 and stats["occupied"] == 1
