from models import Room, RoomType
from repository import RoomRepository


def make_room(number="101"):
    return Room(0, number, RoomType.SINGLE, 1, 3000, 1)


def test_add_assigns_ids():
    repo = RoomRepository()
    assert repo.add(make_room("101")).id == 1
    assert repo.add(make_room("102")).id == 2
    assert repo.count() == 2


def test_delete_and_get_missing():
    repo = RoomRepository()
    room = repo.add(make_room())
    assert repo.delete(room.id) is True
    assert repo.get(room.id) is None
    assert repo.delete(room.id) is False


def test_returned_objects_are_copies():
    repo = RoomRepository()
    room = repo.add(make_room())
    room.price = 1
    assert repo.get(room.id).price == 3000
