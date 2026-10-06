"""MongoRepository — вся работа с MongoDB."""

from datetime import datetime

from pymongo import ASCENDING, DESCENDING, ReturnDocument

from app.models import Train


class NotFoundError(LookupError):
    pass


class MongoRepository:
    def __init__(self, db) -> None:
        self.db = db
        self.trains = db["trains"]

    # ---------- служебное ----------
    def _next_id(self) -> int:
        counter = self.db["counters"].find_one_and_update(
            {"_id": "trains"}, {"$inc": {"value": 1}}, upsert=True, return_document=ReturnDocument.AFTER)
        return counter["value"]

    def create_indexes(self) -> list[str]:
        return [
            self.trains.create_index("number", unique=True),                                   # поиск по номеру
            self.trains.create_index([("route.from.city", ASCENDING), ("route.to.city", ASCENDING)]),
            self.trains.create_index("cities"),                                               # multikey по массиву
            self.trains.create_index("departure_time"),
        ]

    # ---------- CRUD ----------
    def insert(self, train: Train) -> dict:
        doc = train.to_document()
        doc["_id"] = self._next_id()
        self.trains.insert_one(doc)
        return doc

    def get(self, train_id: int) -> dict | None:
        return self.trains.find_one({"_id": train_id})

    def get_by_number(self, number: str) -> dict | None:
        return self.trains.find_one({"number": number})

    def list_trains(self, skip: int = 0, limit: int = 20) -> list[dict]:
        return list(self.trains.find().sort("_id", ASCENDING).skip(skip).limit(limit))

    def replace(self, train_id: int, train: Train) -> dict:
        doc = train.to_document()
        doc["_id"] = train_id
        result = self.trains.replace_one({"_id": train_id}, doc)
        if result.matched_count == 0:
            raise NotFoundError(f"Поезд {train_id} не найден")
        return doc

    def update_fields(self, train_id: int, fields: dict) -> dict:
        doc = self.trains.find_one_and_update({"_id": train_id}, {"$set": fields},
                                              return_document=ReturnDocument.AFTER)
        if doc is None:
            raise NotFoundError(f"Поезд {train_id} не найден")
        return doc

    def delete(self, train_id: int) -> bool:
        return self.trains.delete_one({"_id": train_id}).deleted_count == 1

    def count(self) -> int:
        return self.trains.count_documents({})

    # ---------- запросы ----------
    def by_status(self, status: str) -> list[dict]:                                  # 1. фильтр
        return list(self.trains.find({"status": status}))

    def by_price(self, min_price: float, max_price: float) -> list[dict]:            # 2. фильтр по диапазону
        return list(self.trains.find({"base_price": {"$gte": min_price, "$lte": max_price}}))

    def with_free_seats(self, minimum: int) -> list[dict]:                           # 3. фильтр + несколько условий
        return list(self.trains.find({"free_seats": {"$gte": minimum}, "status": "scheduled"}))

    def by_route(self, from_city: str, to_city: str) -> list[dict]:                  # 4. вложенные поля
        return list(self.trains.find({"route.from.city": from_city, "route.to.city": to_city})
                    .sort("departure_time", ASCENDING))

    def through_city(self, city: str) -> list[dict]:                                 # 5. элемент массива
        return list(self.trains.find({"cities": city}))

    def with_wagon_type(self, wagon_type: str) -> list[dict]:                        # 6. массив вложенных документов
        result = []
        for doc in self.trains.find({"wagons.type": wagon_type}, {"number": 1, "name": 1, "wagons": 1}):
            doc["wagons"] = [w for w in doc["wagons"] if w["type"] == wagon_type]
            result.append(doc)
        return result

    def sorted_by_departure(self) -> list[dict]:                                     # 7. сортировка
        projection = {"number": 1, "name": 1, "route": 1, "departure_time": 1, "base_price": 1, "status": 1, "free_seats": 1}
        return list(self.trains.find({}, projection).sort("departure_time", ASCENDING))

    def cheapest(self, limit: int = 5) -> list[dict]:                                # 8. сортировка + limit
        return list(self.trains.find({"status": "scheduled"}).sort("base_price", ASCENDING).limit(limit))

    def departing_between(self, start: datetime, end: datetime) -> list[dict]:       # 9. фильтр по дате
        return list(self.trains.find({"departure_time": {"$gte": start, "$lt": end}}).sort("departure_time", ASCENDING))

    def count_by_status(self) -> list[dict]:                                         # 10. агрегация
        return list(self.trains.aggregate([
            {"$group": {"_id": "$status", "trains": {"$sum": 1}}},
            {"$sort": {"trains": DESCENDING}},
        ]))

    def price_by_category(self) -> list[dict]:                                       # 11. агрегация
        return list(self.trains.aggregate([
            {"$match": {"status": {"$ne": "cancelled"}}},
            {"$group": {"_id": "$category", "avg_price": {"$avg": "$base_price"},
                        "min_price": {"$min": "$base_price"}, "max_price": {"$max": "$base_price"},
                        "trains": {"$sum": 1}}},
            {"$sort": {"avg_price": DESCENDING}},
        ]))

    def seats_by_wagon_type(self) -> list[dict]:                                     # 12. агрегация с $unwind
        return list(self.trains.aggregate([
            {"$unwind": "$wagons"},
            {"$group": {"_id": "$wagons.type", "wagons": {"$sum": 1}, "seats": {"$sum": "$wagons.seats"}}},
            {"$sort": {"seats": DESCENDING}},
        ]))

    def top_popular_directions(self, limit: int = 3) -> list[dict]:                  # 13. TOP-N направлений
        return list(self.trains.aggregate([
            {"$group": {"_id": {"from": "$route.from.city", "to": "$route.to.city"}, "trains": {"$sum": 1}}},
            {"$sort": {"trains": DESCENDING}},
            {"$limit": limit},
        ]))

    # ---------- изменение вложенного массива ----------
    def book_seat(self, train_id: int, wagon_number: int, seat: int) -> dict | None:
        """Бронирование с оптимистической блокировкой: обновление пройдёт, только если документ
        не изменился с момента чтения (поле version). Изменение одного документа в MongoDB атомарно."""
        doc = self.get(train_id)
        if doc is None or doc["status"] != "scheduled":
            return None
        wagon = next((w for w in doc["wagons"] if w["number"] == wagon_number), None)
        if wagon is None or not 1 <= seat <= wagon["seats"] or seat in wagon["booked"]:
            return None
        wagon["booked"].append(seat)
        result = self.trains.update_one(
            {"_id": train_id, "version": doc.get("version", 0)},
            {"$set": {"wagons": doc["wagons"], "free_seats": doc["free_seats"] - 1},
             "$inc": {"version": 1}})
        return self.get(train_id) if result.modified_count == 1 else None
