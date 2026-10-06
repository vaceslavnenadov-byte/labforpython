"""Application Factory."""

import logging
import time

from flask import Flask, g, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from app.config import Config
from app.database import Base, close_session, init_engine, make_session_factory
from app.exceptions import AppError
from app.seed import seed


def create_app(config: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config)
    app.json.ensure_ascii = False
    app.json.sort_keys = False
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logger = logging.getLogger("taxi")

    engine = init_engine(app.config["DATABASE_URL"])
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    app.extensions["session_factory"] = factory
    with factory() as db:
        seed(db)
    app.teardown_appcontext(close_session)

    from app.routes.api import api
    from app.routes.web import web
    app.register_blueprint(web)
    app.register_blueprint(api)

    @app.before_request
    def start_timer():
        g.start = time.perf_counter()

    @app.after_request
    def log_request(response):
        if not request.path.startswith("/static"):
            logger.info("%s %s -> %s (%.1f ms)", request.method, request.path, response.status_code,
                        (time.perf_counter() - g.get("start", time.perf_counter())) * 1000)
        return response

    def wants_json() -> bool:
        return request.path.startswith("/api/")

    @app.errorhandler(AppError)
    def app_error(error: AppError):
        if wants_json():
            return jsonify({"error": error.message}), error.status_code
        return render_template("error.html", code=error.status_code, message=error.message), error.status_code

    @app.errorhandler(404)
    def not_found(error):
        if wants_json():
            return jsonify({"error": "Ресурс не найден"}), 404
        return render_template("404.html"), 404

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException):
        if wants_json():
            return jsonify({"error": error.description}), error.code
        return render_template("error.html", code=error.code, message=error.description), error.code

    @app.errorhandler(Exception)
    def internal_error(error):
        logger.exception("Внутренняя ошибка")
        if wants_json():
            return jsonify({"error": "Внутренняя ошибка сервера"}), 500
        return render_template("error.html", code=500, message="Внутренняя ошибка сервера"), 500

    logger.info("Приложение запущено, БД: %s", engine.url.render_as_string(hide_password=True))
    return app
