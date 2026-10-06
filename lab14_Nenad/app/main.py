"""
ЛР №14. REST API на FastAPI. Вариант 10 — Железная дорога (/trains).

Запуск: uvicorn app.main:app --reload     Документация: http://127.0.0.1:8000/docs и /redoc
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.cache import cache
from app.database import Base, SessionLocal, engine
from app.exceptions import AppError
from app.routers import auth, trains
from app.seed import seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("railway-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    logger.info("Application started, cache enabled: %s", cache.enabled)
    yield


app = FastAPI(title="Railway API", version="1.0.0", lifespan=lifespan,
              description="ЛР №14, вариант 10. Поезда: CRUD, поиск, фильтрация, сортировка, пагинация, статистика.")
app.include_router(trains.router)
app.include_router(auth.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    logger.info("%s %s -> %s %.1f ms", request.method, request.url.path, response.status_code,
                (time.perf_counter() - start) * 1000)
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, error: AppError):
    return JSONResponse(status_code=error.status_code, content={"error": error.message, "code": error.code})


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, error: RequestValidationError):
    details = [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors()]
    return JSONResponse(status_code=422, content={"error": "; ".join(details), "code": "VALIDATION_ERROR"})


@app.exception_handler(Exception)
async def unexpected_handler(request: Request, error: Exception):
    logger.exception("Unhandled error")      # traceback только в журнале, клиенту — нет
    return JSONResponse(status_code=500, content={"error": "Internal server error", "code": "INTERNAL_ERROR"})


@app.get("/health", tags=["Служебное"])
async def health():
    return {"status": "healthy", "cache": cache.enabled}
