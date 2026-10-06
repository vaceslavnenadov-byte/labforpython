"""Pydantic-схемы с валидацией входных данных."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.app.models import CarClass, DriverStatus, OrderStatus, Role

PHONE = r"^\+7\d{10}$"


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(pattern=PHONE, examples=["+79001112233"])


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    phone: str
    role: Role


class CarIn(BaseModel):
    plate: str = Field(min_length=6, max_length=12, examples=["А001АА777"])
    model: str = Field(min_length=2, max_length=80)
    car_class: CarClass
    year: int = Field(ge=1990, le=2100)


class CarOut(CarIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class DriverIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(pattern=PHONE)
    license_number: str = Field(min_length=6, max_length=20)
    car_id: int | None = None


class DriverUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=120)
    status: DriverStatus | None = None
    car_id: int | None = None
    rating: float | None = Field(None, ge=1, le=5)


class DriverOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    phone: str
    license_number: str
    rating: float
    status: DriverStatus
    car: CarOut | None


class QuoteIn(BaseModel):
    distance_km: float = Field(gt=0, le=300)
    car_class: CarClass


class QuoteOut(BaseModel):
    car_class: CarClass
    distance_km: float
    surge: float
    price: float


class OrderIn(QuoteIn):
    pickup: str = Field(min_length=3, max_length=200)
    destination: str = Field(min_length=3, max_length=200)

    @field_validator("destination")
    @classmethod
    def different_addresses(cls, value: str, info):
        if info.data.get("pickup", "").strip().lower() == value.strip().lower():
            raise ValueError("pickup and destination must differ")
        return value


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    passenger_id: int
    driver_id: int | None
    pickup: str
    destination: str
    distance_km: float
    car_class: CarClass
    status: OrderStatus
    price: float
    surge: float
    created_at: datetime
    finished_at: datetime | None


class OrderList(BaseModel):
    items: list[OrderOut]
    total: int
    skip: int
    limit: int


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    text: str
    created_at: datetime
