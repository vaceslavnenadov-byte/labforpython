"""Автомобили и водители: читать могут все авторизованные, изменять — только ADMIN."""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from src.app.api.deps import current_user, get_cache, get_db, require_admin
from src.app.cache import Cache
from src.app.models import CarClass, DriverStatus
from src.app.schemas import CarIn, CarOut, DriverIn, DriverOut, DriverUpdate
from src.app.services.services import FleetService

router = APIRouter(tags=["fleet"])


def service(db: Session = Depends(get_db), cache: Cache = Depends(get_cache)) -> FleetService:
    return FleetService(db, cache)


@router.get("/cars", response_model=list[CarOut], dependencies=[Depends(current_user)])
def list_cars(fleet: FleetService = Depends(service)):
    return fleet.list_cars()


@router.post("/cars", response_model=CarOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
def create_car(data: CarIn, fleet: FleetService = Depends(service)):
    return fleet.create_car(data)


@router.delete("/cars/{car_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_car(car_id: int, fleet: FleetService = Depends(service)):
    fleet.delete_car(car_id)


@router.get("/drivers", response_model=list[DriverOut], dependencies=[Depends(current_user)])
def list_drivers(status_: DriverStatus | None = Query(None, alias="status"), car_class: CarClass | None = None,
                 sort: str = Query("rating", pattern="^(rating|name)$"), fleet: FleetService = Depends(service)):
    """Фильтрация по статусу и классу автомобиля, сортировка по рейтингу или имени."""
    return fleet.list_drivers(status_, car_class, sort)


@router.get("/drivers/{driver_id}", response_model=DriverOut, dependencies=[Depends(current_user)])
def get_driver(driver_id: int, response: Response, fleet: FleetService = Depends(service)):
    hits = fleet.cache.hits
    data = fleet.get_driver(driver_id)
    response.headers["X-Cache"] = "HIT" if fleet.cache.hits > hits else "MISS"
    return data


@router.post("/drivers", response_model=DriverOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
def create_driver(data: DriverIn, fleet: FleetService = Depends(service)):
    return fleet.create_driver(data)


@router.patch("/drivers/{driver_id}", response_model=DriverOut, dependencies=[Depends(require_admin)])
def update_driver(driver_id: int, data: DriverUpdate, fleet: FleetService = Depends(service)):
    return fleet.update_driver(driver_id, data)


@router.delete("/drivers/{driver_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
def delete_driver(driver_id: int, fleet: FleetService = Depends(service)):
    fleet.delete_driver(driver_id)
