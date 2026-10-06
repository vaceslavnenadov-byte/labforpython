"""Бизнес-логика: MongoDB — основное хранилище, Redis — быстрый доступ."""

import json
import time
from datetime import datetime

from app.cache import RedisCache
from app.models import STATUSES, validate_train
from app.repository import MongoRepository, NotFoundError


class TrainService:
    def __init__(self, repo: MongoRepository, cache: RedisCache) -> None:
        self.repo = repo
        self.cache = cache

    # ---------- чтение через Cache-Aside ----------
    def get_train(self, train_id: int) -> tuple[dict, str]:
        """Возвращает (документ, источник)."""
        doc = self.cache.get_train(train_id)
        if doc is not None:
            return doc, "redis"
        locked = self.cache.acquire_lock(train_id)
        try:
            doc = self.repo.get(train_id)
            if doc is None:
                raise NotFoundError(f"Поезд {train_id} не найден")
            if locked:
                self.cache.set_train(doc)
                self.cache.set_seats(train_id, {w["number"]: w["seats"] - len(w["booked"]) for w in doc["wagons"]})
            return json.loads(json.dumps(doc, default=str)), "mongodb"
        finally:
            if locked:
                self.cache.release_lock(train_id)

    # ---------- изменения (с инвалидированием кэша) ----------
    def _sync_indexes(self, doc: dict) -> None:
        self.cache.add_departure(doc["_id"], doc["number"], doc["departure_time"])
        self.cache.mark_active(doc["number"], doc["status"] == "scheduled")

    def add_train(self, data: dict) -> dict:
        train = validate_train(data)
        if self.repo.get_by_number(train.number):
            raise ValueError(f"Поезд {train.number} уже существует")
        doc = self.repo.insert(train)
        self._sync_indexes(doc)
        self.cache.publish("train.created", doc["_id"])
        return doc

    def update_train(self, train_id: int, fields: dict) -> dict:
        allowed = {"name", "base_price", "status", "category"}
        if not fields or set(fields) - allowed:
            raise ValueError(f"Можно изменять только поля {sorted(allowed)}")
        if "status" in fields and fields["status"] not in STATUSES:
            raise ValueError(f"Статус должен быть одним из {STATUSES}")
        if "base_price" in fields:
            fields["base_price"] = float(fields["base_price"])
            if fields["base_price"] <= 0:
                raise ValueError("Цена должна быть положительной")
        doc = self.repo.update_fields(train_id, fields)
        self.cache.invalidate(train_id)              # кэш больше не актуален
        self._sync_indexes(doc)
        self.cache.publish("train.updated", train_id)
        return doc

    def delete_train(self, train_id: int) -> None:
        doc = self.repo.get(train_id)
        if doc is None:
            raise NotFoundError(f"Поезд {train_id} не найден")
        self.repo.delete(train_id)
        self.cache.invalidate(train_id)
        self.cache.remove_departure(train_id, doc["number"])
        self.cache.mark_active(doc["number"], False)
        self.cache.publish("train.deleted", train_id)

    def book_seat(self, train_id: int, wagon: int, seat: int) -> dict:
        doc = self.repo.book_seat(train_id, wagon, seat)
        if doc is None:
            raise ValueError("Место занято, не существует или продажа билетов закрыта")
        self.cache.invalidate(train_id)
        return doc

    # ---------- поиск ----------
    def search(self, from_city: str, to_city: str) -> list[dict]:
        self.cache.push_search(f"{from_city} → {to_city}")
        return self.repo.by_route(from_city, to_city)

    def available_seats(self, train_id: int) -> tuple[dict[int, int], str]:
        seats = self.cache.get_seats(train_id)
        if seats is not None:
            return seats, "redis"
        doc, _ = self.get_train(train_id)
        return {w["number"]: w["seats"] - len(w["booked"]) for w in doc["wagons"]}, "mongodb"

    def nearest_departures(self, after: datetime, limit: int = 5):
        if not self.cache.r.exists("departures"):          # первичное заполнение из MongoDB
            for doc in self.repo.sorted_by_departure():
                full = self.repo.get(doc["_id"])
                self._sync_indexes(full)
        return self.cache.nearest_departures(after, limit)

    def statistics(self) -> dict:
        return {
            "total": self.repo.count(),
            "by_status": self.repo.count_by_status(),
            "price_by_category": self.repo.price_by_category(),
            "seats_by_wagon_type": self.repo.seats_by_wagon_type(),
            "top_directions": self.repo.top_popular_directions(),
        }

    # ---------- эксперимент ----------
    def benchmark(self, train_id: int, counts=(100, 1000, 10000)) -> list[tuple[int, float, float]]:
        self.get_train(train_id)                   # прогрев кэша
        results = []
        for n in counts:
            start = time.perf_counter()
            for _ in range(n):
                self.repo.get(train_id)
            mongo = time.perf_counter() - start
            start = time.perf_counter()
            for _ in range(n):
                json.loads(self.cache.r.get(f"train:{train_id}"))
            redis_time = time.perf_counter() - start
            results.append((n, mongo, redis_time))
        return results
