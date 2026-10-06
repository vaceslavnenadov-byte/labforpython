"""
ЛР №11. Реляционная БД (SQLite, чистый SQL), Redis-кэш и CDN.
Вариант 10. Железная дорога: Train; Redis — состояние расписания; CDN — схемы вагонов.

Запуск: python app.py  (http://127.0.0.1:5000)
"""

import logging
import os
import threading

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from cache import RedisCache, create_cache
from database import ensure_db
from exceptions import ApiError, ValidationError
from repository import TicketRepository, TrainRepository
from service import RailwayService

CDN_BASE_URL = os.getenv("CDN_BASE_URL", "http://127.0.0.1:8081")


def create_app(connection=None, cache: RedisCache | None = None) -> Flask:
    app = Flask(__name__)
    app.json.ensure_ascii = False
    app.json.sort_keys = False
    connection = connection or ensure_db()
    service = RailwayService(TrainRepository(connection), TicketRepository(connection), cache or create_cache())
    lock = threading.Lock()  # одно соединение SQLite на процесс — сериализуем запросы

    def body() -> dict:
        data = request.get_json(silent=True)
        if data is None:
            raise ValidationError("Body must be valid JSON")
        return data

    def number(name):
        value = request.args.get(name)
        try:
            return float(value) if value is not None else None
        except ValueError:
            raise ValidationError(f"{name} must be a number") from None

    @app.before_request
    def acquire():
        lock.acquire()
        service.cache.count_request()

    @app.teardown_request
    def release(exc):
        if lock.locked():
            lock.release()

    @app.get("/trains")
    def list_trains():
        return jsonify(service.list_trains(request.args.get("status"), number("min_price"), number("max_price"),
                                           request.args.get("sort", "number"), request.args.get("order", "asc")))

    @app.get("/trains/<int:train_id>")
    def get_train(train_id):
        train = service.get_train(train_id)
        # статические схемы вагонов отдаются через CDN, в БД хранится только ссылка-шаблон
        for wagon in train["wagons"]:
            wagon["scheme_url"] = f"{CDN_BASE_URL}/static/images/{wagon['wagon_type']}.svg"
        return jsonify(train)

    @app.post("/trains")
    def create_train():
        return jsonify(service.create_train(body())), 201

    @app.put("/trains/<int:train_id>")
    def put_train(train_id):
        return jsonify(service.update_train(train_id, body(), partial=False))

    @app.patch("/trains/<int:train_id>")
    def patch_train(train_id):
        return jsonify(service.update_train(train_id, body(), partial=True))

    @app.delete("/trains/<int:train_id>")
    def delete_train(train_id):
        service.delete_train(train_id)
        return "", 204

    @app.get("/trains/<int:train_id>/schedule")
    def schedule(train_id):
        return jsonify(service.schedule(train_id))

    @app.get("/trains/<int:train_id>/free-seats")
    def free_seats(train_id):
        return jsonify(service.free_seats(train_id))

    @app.get("/search")
    def search():
        return jsonify(service.search(request.args.get("from", ""), request.args.get("to", "")))

    @app.post("/tickets")
    def buy_ticket():
        return jsonify(service.buy_ticket(body())), 201

    @app.post("/tickets/<int:ticket_id>/return")
    def return_ticket(ticket_id):
        return jsonify(service.return_ticket(ticket_id))

    @app.get("/stats/cache")
    def cache_stats():
        return jsonify({"popular_trains": service.cache.popular(),
                        "search_history": service.cache.search_history(),
                        "requests_total": service.cache.count_request()})

    @app.errorhandler(ApiError)
    def api_error(error):
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify({"error": error.description, "code": error.name.upper().replace(" ", "_")}), error.code

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_app().run(port=5000)
