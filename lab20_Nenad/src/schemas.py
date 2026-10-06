from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.models import CarClass, RideStatus


class DriverIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    car_plate: str = Field(min_length=6, max_length=12)
    car_class: CarClass


class DriverOut(DriverIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class RideIn(BaseModel):
    passenger: str = Field(min_length=2, max_length=120)
    driver_id: int = Field(gt=0)
    pickup: str = Field(min_length=2, max_length=200)
    destination: str = Field(min_length=2, max_length=200)
    distance_km: float = Field(gt=0, le=500)


class RideOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    passenger: str
    driver_id: int
    pickup: str
    destination: str
    distance_km: float
    cost: float
    status: RideStatus
    created_at: datetime


class StatusIn(BaseModel):
    status: RideStatus
