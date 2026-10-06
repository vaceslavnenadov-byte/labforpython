"""HTTP-слой /trains."""

import logging
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.cache import Cache, get_cache
from app.database import get_db
from app.models.train import TrainStatus, User
from app.repositories.train import TrainRepository
from app.schemas.train import ErrorResponse, TrainCreate, TrainListResponse, TrainResponse, TrainStatistics, TrainUpdate
from app.security import require_admin
from app.services.train import TrainService

router = APIRouter(prefix="/trains", tags=["Поезда"])
audit = logging.getLogger("audit")
NOT_FOUND = {404: {"model": ErrorResponse, "description": "Поезд не найден"}}


def get_service(db: Session = Depends(get_db), cache: Cache = Depends(get_cache)) -> TrainService:
    return TrainService(TrainRepository(db), cache)


def write_audit(action: str, train_id: int, user: str) -> None:
    """Фоновая задача: выполняется после отправки ответа клиенту."""
    audit.info("%s train=%s by=%s", action, train_id, user)


@router.get("", response_model=TrainListResponse, summary="Список поездов",
            description="Фильтрация, сортировка и пагинация")
def list_trains(status_: TrainStatus | None = Query(None, alias="status"),
                route: str | None = Query(None, description="Часть маршрута, например «Казань»"),
                departure_date: date | None = None,
                min_price: float | None = Query(None, ge=0), max_price: float | None = Query(None, ge=0),
                sort: str = Query("departure_time", description="number | departure_time | price | wagons_count"),
                order: str = Query("asc", pattern="^(asc|desc)$"),
                skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100),
                service: TrainService = Depends(get_service)):
    items, total = service.list_trains(status=status_, route=route, departure_date=departure_date,
                                       min_price=min_price, max_price=max_price, sort=sort, order=order,
                                       skip=skip, limit=limit)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/search", response_model=list[TrainResponse], summary="Поиск по номеру, маршруту и станциям")
async def search_trains(q: str = Query(min_length=2), service: TrainService = Depends(get_service)):
    # синхронный запрос к БД выполняем в пуле потоков, чтобы не блокировать event loop
    return await run_in_threadpool(service.search, q)


@router.get("/statistics", response_model=TrainStatistics, summary="Статистика")
def statistics(service: TrainService = Depends(get_service)):
    return service.statistics()


@router.get("/{train_id}", response_model=TrainResponse, responses=NOT_FOUND, summary="Поезд по id")
def get_train(train_id: int, response: Response, service: TrainService = Depends(get_service)):
    data, from_cache = service.get_train(train_id)
    response.headers["X-Cache"] = "HIT" if from_cache else "MISS"
    return data


@router.post("", response_model=TrainResponse, status_code=status.HTTP_201_CREATED,
             responses={409: {"model": ErrorResponse}}, summary="Создать поезд (ADMIN)")
def create_train(data: TrainCreate, background: BackgroundTasks, service: TrainService = Depends(get_service),
                 admin: User = Depends(require_admin)):
    train = service.create_train(data)
    background.add_task(write_audit, "create", train.id, admin.username)
    return train


@router.put("/{train_id}", response_model=TrainResponse, responses=NOT_FOUND, summary="Полная замена (ADMIN)")
def replace_train(train_id: int, data: TrainCreate, service: TrainService = Depends(get_service),
                  admin: User = Depends(require_admin)):
    return service.replace_train(train_id, data)


@router.patch("/{train_id}", response_model=TrainResponse, responses=NOT_FOUND, summary="Частичное изменение (ADMIN)")
def patch_train(train_id: int, data: TrainUpdate, service: TrainService = Depends(get_service),
                admin: User = Depends(require_admin)):
    return service.patch_train(train_id, data)


@router.delete("/{train_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND, summary="Удалить (ADMIN)")
def delete_train(train_id: int, background: BackgroundTasks, service: TrainService = Depends(get_service),
                 admin: User = Depends(require_admin)):
    service.delete_train(train_id)
    background.add_task(write_audit, "delete", train_id, admin.username)
    return Response(status_code=204)
