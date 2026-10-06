"""Taxi API — точка входа FastAPI.

Запуск: uvicorn src.app.main:app --reload
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from src.app.api import auth, fleet, orders
from src.app.cache import Cache, create_cache
from src.app.config import Settings, load_settings
from src.app.database import make_engine, make_session_factory
from src.app.events import create_broker
from src.app.exceptions import AppException
from src.app.models import Base
from src.app.seed import ensure_admin, seed_fleet

logger = logging.getLogger("taxi.api")


def error(status: int, code: str, message, request_id: str | None = None) -> JSONResponse:
    return JSONResponse({"error": code, "message": message}, status_code=status,
                        headers={"X-Request-ID": request_id} if request_id else None)


def create_app(settings: Settings | None = None, cache: Cache | None = None, broker=None,
               seed: bool = True) -> FastAPI:
    settings = settings or load_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    engine = make_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            Base.metadata.create_all(engine)
            with app.state.session_factory() as db:
                ensure_admin(db, settings.admin_email, settings.admin_password)
                if seed:
                    seed_fleet(db)
        except OperationalError as exc:      # приложение стартует, /health отвечает 503 до восстановления БД
            logger.error("database unavailable at startup: %s", exc.orig)
        logger.info("Taxi API started (env=%s)", settings.app_env)
        yield
        engine.dispose()

    app = FastAPI(title="Taxi API", version="1.0.0", lifespan=lifespan,
                  description="Итоговый проект: заказ такси (FastAPI + PostgreSQL + Redis + брокер сообщений)")
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.cache = cache or create_cache(settings.redis_url, settings.cache_ttl)
    app.state.broker = broker or create_broker(settings.broker_url)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info("%s %s -> %s %.1fms [%s]", request.method, request.url.path, response.status_code,
                    (time.perf_counter() - started) * 1000, request_id)
        return response

    @app.exception_handler(AppException)
    async def app_exception(request: Request, exc: AppException):
        logger.warning("%s: %s", exc.error, exc.message)
        return error(exc.status_code, exc.error, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation(request: Request, exc: RequestValidationError):
        details = [f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in exc.errors()]
        return error(422, "VALIDATION_ERROR", "; ".join(details))

    @app.exception_handler(IntegrityError)
    async def integrity(request: Request, exc: IntegrityError):
        logger.warning("integrity error: %s", exc.orig)
        return error(409, "CONFLICT", "Data conflicts with existing records")

    @app.exception_handler(OperationalError)
    async def database_down(request: Request, exc: OperationalError):
        logger.error("database unavailable: %s", exc.orig)
        return error(503, "DATABASE_UNAVAILABLE", "Database is temporarily unavailable")

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        logger.exception("unhandled error")
        return error(500, "INTERNAL_ERROR", "Internal server error")

    @app.get("/health", tags=["system"])
    def health():
        """Состояние зависимостей. БД обязательна (503), Redis и брокер — деградация без отказа."""
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            database = "ok"
        except Exception:
            database = "down"
        body = {"status": "ok" if database == "ok" else "error", "database": database,
                "redis": "ok" if app.state.cache.ping() else "unavailable",
                "broker": "ok" if app.state.broker.ping() else "unavailable"}
        if database == "ok" and "unavailable" in body.values():
            body["status"] = "degraded"
        return JSONResponse(body, status_code=200 if database == "ok" else 503)

    app.include_router(auth.router)
    app.include_router(fleet.router)
    app.include_router(orders.router)
    return app


app = create_app()
