"""Хранение номеров в памяти процесса. Потокобезопасно (RLock)."""

import threading
from copy import deepcopy

from models import Room


class RoomRepository:
    def __init__(self) -> None:
        self._rooms: dict[int, Room] = {}
        self._next_id = 1
        self._lock = threading.RLock()

    def add(self, room: Room) -> Room:
        with self._lock:
            room.id = self._next_id
            self._next_id += 1
            self._rooms[room.id] = room
            return deepcopy(room)

    def get(self, room_id: int) -> Room | None:
        with self._lock:
            room = self._rooms.get(room_id)
            return deepcopy(room) if room else None

    def get_all(self) -> list[Room]:
        with self._lock:
            return [deepcopy(r) for r in self._rooms.values()]

    def update(self, room: Room) -> Room:
        with self._lock:
            if room.id not in self._rooms:
                raise KeyError(room.id)
            self._rooms[room.id] = deepcopy(room)
            return deepcopy(room)

    def delete(self, room_id: int) -> bool:
        with self._lock:
            return self._rooms.pop(room_id, None) is not None

    def count(self) -> int:
        with self._lock:
            return len(self._rooms)

    @property
    def lock(self) -> threading.RLock:
        return self._lock
