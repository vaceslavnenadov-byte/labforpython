"""Pydantic-схемы: что API принимает и что возвращает."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.models.train import TrainStatus


class TrainBase(BaseModel):
    number: str = Field(min_length=2, max_length=10, examples=["001А"])
    route: str = Field(min_length=3, max_length=120, examples=["Москва - Санкт-Петербург"])
    stations: list[str] = Field(min_length=2, examples=[["Москва", "Тверь", "Санкт-Петербург"]])
    departure_time: datetime = Field(examples=["2026-10-10T23:55:00"])
    arrival_time: datetime = Field(examples=["2026-10-11T07:55:00"])
    wagons_count: int = Field(gt=0, le=30, examples=[12])
    price: float = Field(gt=0, examples=[3200])
    status: TrainStatus = TrainStatus.SCHEDULED


class TrainCreate(TrainBase):
    @model_validator(mode="after")
    def check_times(self):
        if self.arrival_time <= self.departure_time:
            raise ValueError("arrival_time must be later than departure_time")
        return self


class TrainUpdate(BaseModel):
    """Для PATCH: все поля необязательны."""
    number: str | None = Field(None, min_length=2, max_length=10)
    route: str | None = Field(None, min_length=3, max_length=120)
    stations: list[str] | None = Field(None, min_length=2)
    departure_time: datetime | None = None
    arrival_time: datetime | None = None
    wagons_count: int | None = Field(None, gt=0, le=30)
    price: float | None = Field(None, gt=0)
    status: TrainStatus | None = None


class TrainResponse(TrainBase):
    model_config = ConfigDict(from_attributes=True)
    id: int

    @computed_field
    @property
    def duration_hours(self) -> float:
        return round((self.arrival_time - self.departure_time).total_seconds() / 3600, 2)


class TrainListResponse(BaseModel):
    items: list[TrainResponse]
    total: int
    skip: int
    limit: int


class TrainStatistics(BaseModel):
    total: int
    average_price: float
    min_price: float
    max_price: float
    average_duration_hours: float
    total_wagons: int
    by_status: dict[str, int]
    by_route: dict[str, int]


class ErrorResponse(BaseModel):
    error: str
    code: str
