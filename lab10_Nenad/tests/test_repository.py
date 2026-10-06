from models import Train
from repository import TrainRepository


def make(number="001А"):
    return Train(0, number, "Москва", "Казань", "2026-10-10T10:00", "2026-10-10T20:00", 2, 10, 0, 1000)


def test_create_assigns_incremental_ids():
    repo = TrainRepository()
    assert [repo.create(make(n)).id for n in ("A", "B")] == [1, 2]


def test_update_and_delete():
    repo = TrainRepository()
    train = repo.create(make())
    train.price = 1500
    repo.update(train)
    assert repo.get_by_id(train.id).price == 1500
    assert repo.delete(train.id) and repo.get_by_id(train.id) is None
