"""
ЛР №20. Вариант 10 — Такси: API + PostgreSQL + Redis в Docker Compose, CI/CD.
Запуск без Docker: uvicorn src.main:app
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.cache import Cache, create_cache
from src.config import Settings, load_settings
from src.models import Base, RideStatus
from src.schemas import DriverIn, DriverOut, RideIn, RideOut, StatusIn
from src.service import Conflict, NotFound, TaxiService


def create_app(settings: Settings | None = None, cache: Cache | None = None) -> FastAPI:
    settings = settings or load_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logger = logging.getLogger("taxi")
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    cache = cache or create_cache(settings.redis_url, settings.cache_ttl)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Base.metadata.create_all(engine)
        logger.info("Application started (env=%s, db=%s, cache=%s)", settings.app_env,
                    engine.url.render_as_string(hide_password=True), "redis" if cache.client else "off")
        yield
        logger.info("Application stopped")

    app = FastAPI(title="Taxi API", version="1.0.0", lifespan=lifespan)

    def get_service():
        with factory() as session:
            yield TaxiService(session, cache)

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        logger.info("%s %s -> %s (%.1f ms)", request.method, request.url.path, response.status_code,
                    (time.perf_counter() - start) * 1000)
        return response

    @app.get("/health")
    def health(response: Response):
        """Проверка самого API, базы данных и Redis. 503, если недоступна БД."""
        status = {"status": "healthy", "database": "up", "cache": "up" if cache.ping() else "off"}
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as error:
            logger.error("health: database unavailable: %s", error)
            status.update(status="unhealthy", database="down")
            response.status_code = 503
        return status

    @app.post("/drivers", response_model=DriverOut, status_code=201)
    def create_driver(data: DriverIn, service: TaxiService = Depends(get_service)):
        try:
            return service.create_driver(data)
        except Conflict as error:
            raise HTTPException(409, str(error)) from None

    @app.get("/drivers", response_model=list[DriverOut])
    def list_drivers(service: TaxiService = Depends(get_service)):
        return service.list_drivers()

    @app.post("/rides", response_model=RideOut, status_code=201)
    def create_ride(data: RideIn, service: TaxiService = Depends(get_service)):
        try:
            return service.create_ride(data)
        except NotFound as error:
            raise HTTPException(404, str(error)) from None
        except Conflict as error:
            raise HTTPException(409, str(error)) from None

    @app.get("/rides", response_model=list[RideOut])
    def list_rides(status: RideStatus | None = None, service: TaxiService = Depends(get_service)):
        return service.list_rides(status)

    @app.get("/rides/{ride_id}", response_model=RideOut)
    def get_ride(ride_id: int, response: Response, service: TaxiService = Depends(get_service)):
        try:
            data, cached = service.get_ride(ride_id)
        except NotFound as error:
            raise HTTPException(404, str(error)) from None
        response.headers["X-Cache"] = "HIT" if cached else "MISS"
        return data

    @app.patch("/rides/{ride_id}/status", response_model=RideOut)
    def change_status(ride_id: int, data: StatusIn, service: TaxiService = Depends(get_service)):
        try:
            return service.change_status(ride_id, data.status)
        except NotFound as error:
            raise HTTPException(404, str(error)) from None
        except Conflict as error:
            raise HTTPException(409, str(error)) from None

    @app.get("/stats")
    def stats(service: TaxiService = Depends(get_service)):
        return service.stats()

    return app


app = create_app()
