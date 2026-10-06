"""
ЛР №10. HTTP и REST API (Flask).
Вариант 10. Железная дорога — ресурс Train, спец. операция «свободные места».

Запуск:  python app.py      (http://127.0.0.1:5000)
"""

import logging
import os
import time

from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException

from exceptions import ApiError
from repository import TrainRepository
from routes import api
from service import TrainService, seed

logger = logging.getLogger("railway-api")


def create_app(api_key: str | None = None, with_seed: bool = True) -> Flask:
    app = Flask(__name__)
    app.json.ensure_ascii = False
    app.json.sort_keys = False
    service = TrainService(TrainRepository())
    if with_seed:
        seed(service)
    app.config["TRAIN_SERVICE"] = service
    app.config["API_KEY"] = api_key if api_key is not None else os.getenv("API_KEY", "secret-key")
    app.register_blueprint(api)

    # ---------- middleware (доп. задания 2–4) ----------
    @app.before_request
    def before():
        g.start = time.perf_counter()
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            if request.headers.get("X-API-Key") != app.config["API_KEY"]:
                return jsonify({"error": "Missing or invalid X-API-Key", "code": "UNAUTHORIZED"}), 401

    @app.after_request
    def after(response):
        duration = (time.perf_counter() - g.get("start", time.perf_counter())) * 1000
        logger.info("%s %s -> %s -> %.1f ms", request.method, request.full_path.rstrip("?"),
                    response.status_code, duration)
        response.headers["X-Response-Time-ms"] = f"{duration:.1f}"
        return response

    # ---------- единый формат ошибок ----------
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        codes = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 400: "BAD_REQUEST"}
        return jsonify({"error": error.description, "code": codes.get(error.code, "HTTP_ERROR")}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception):
        logger.exception("Unhandled error")
        return jsonify({"error": "Internal server error", "code": "INTERNAL_ERROR"}), 500

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    create_app().run(host="127.0.0.1", port=5000, debug=False)
