"""Хранение поездов в памяти (БД появится в ЛР №11)."""

from copy import deepcopy

from models import Train


class TrainRepository:
    def __init__(self) -> None:
        self._items: dict[int, Train] = {}
        self._next_id = 1

    def get_all(self) -> list[Train]:
        return [deepcopy(t) for t in self._items.values()]

    def get_by_id(self, train_id: int) -> Train | None:
        train = self._items.get(train_id)
        return deepcopy(train) if train else None

    def create(self, train: Train) -> Train:
        train.id = self._next_id
        self._next_id += 1
        self._items[train.id] = deepcopy(train)
        return deepcopy(train)

    def update(self, train: Train) -> Train:
        self._items[train.id] = deepcopy(train)
        return deepcopy(train)

    def delete(self, train_id: int) -> bool:
        return self._items.pop(train_id, None) is not None
