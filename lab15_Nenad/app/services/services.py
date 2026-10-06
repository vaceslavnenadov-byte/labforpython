"""Бизнес-логика такси: расчёт стоимости, создание/изменение поездок, проверки."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.models import CarClass, Client, Driver, Trip, TripStatus
from app.repositories.repositories import ClientRepository, DriverRepository, TripRepository

TARIFFS = {CarClass.ECONOMY: (99, 14, 6), CarClass.COMFORT: (149, 19, 8), CarClass.BUSINESS: (299, 32, 12)}
TRIP_FIELDS = {"client_id", "driver_id", "pickup", "destination", "distance_km", "duration_min", "status"}


def calculate_cost(car_class: CarClass, distance_km: float, duration_min: int) -> float:
    base, per_km, per_min = TARIFFS[car_class]
    return round(base + per_km * distance_km + per_min * duration_min, 2)


class TaxiService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.trips = TripRepository(db)
        self.drivers = DriverRepository(db)
        self.clients = ClientRepository(db)

    def _commit(self) -> None:
        try:
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            text = str(error.orig).lower()
            if "unique" in text or "duplicate" in text:
                raise ConflictError("Запись с таким телефоном или номером машины уже существует") from None
            raise ValidationError("Нарушение ограничений базы данных") from None

    @staticmethod
    def _clean_trip(data: dict, partial: bool) -> dict:
        unknown = set(data) - TRIP_FIELDS
        if unknown:
            raise ValidationError(f"Неизвестные поля: {', '.join(sorted(unknown))}")
        required = TRIP_FIELDS - {"status"}
        if not partial and not required <= {k for k, v in data.items() if v not in (None, "")}:
            raise ValidationError("Заполните все поля поездки")
        clean = {}
        for key in ("pickup", "destination"):
            if key in data:
                if not str(data[key]).strip():
                    raise ValidationError("Адрес не может быть пустым")
                clean[key] = str(data[key]).strip()
        for key, cast in (("client_id", int), ("driver_id", int), ("distance_km", float), ("duration_min", int)):
            if key in data:
                try:
                    clean[key] = cast(data[key])
                except (TypeError, ValueError):
                    raise ValidationError(f"Поле {key} должно быть числом") from None
                if clean[key] <= 0:
                    raise ValidationError(f"Поле {key} должно быть положительным")
        if "status" in data and data["status"]:
            try:
                clean["status"] = TripStatus(data["status"])
            except ValueError:
                raise ValidationError("Неизвестный статус") from None
        return clean

    def get_trip(self, trip_id: int) -> Trip:
        trip = self.trips.get(trip_id)
        if trip is None:
            raise NotFoundError(f"Поездка №{trip_id} не найдена")
        return trip

    def create_trip(self, data: dict) -> Trip:
        clean = self._clean_trip(data, partial=False)
        driver = self.drivers.get(clean["driver_id"])
        if driver is None:
            raise NotFoundError("Водитель не найден")
        if self.clients.get(clean["client_id"]) is None:
            raise NotFoundError("Клиент не найден")
        clean["cost"] = calculate_cost(driver.car_class, clean["distance_km"], clean["duration_min"])
        trip = self.trips.add(Trip(**clean))
        self._commit()
        return trip

    def update_trip(self, trip_id: int, data: dict, partial: bool = True) -> Trip:
        trip = self.get_trip(trip_id)
        clean = self._clean_trip(data, partial)
        if trip.status in (TripStatus.COMPLETED, TripStatus.CANCELLED) and set(clean) - {"status"}:
            raise ConflictError("Завершённую или отменённую поездку изменить нельзя")
        if "driver_id" in clean and self.drivers.get(clean["driver_id"]) is None:
            raise NotFoundError("Водитель не найден")
        if "client_id" in clean and self.clients.get(clean["client_id"]) is None:
            raise NotFoundError("Клиент не найден")
        for key, value in clean.items():
            setattr(trip, key, value)
        self.db.flush()
        self.db.refresh(trip)
        trip.cost = 0 if trip.status == TripStatus.CANCELLED else calculate_cost(
            trip.driver.car_class, trip.distance_km, trip.duration_min)
        self._commit()
        return trip

    def delete_trip(self, trip_id: int) -> None:
        trip = self.get_trip(trip_id)
        if trip.status == TripStatus.IN_PROGRESS:
            raise ConflictError("Нельзя удалить поездку, которая выполняется")
        self.trips.delete(trip)
        self._commit()

    def create_driver(self, data: dict) -> Driver:
        try:
            driver = Driver(full_name=data["full_name"].strip(), phone=data["phone"].strip(),
                            car_model=data["car_model"].strip(), car_plate=data["car_plate"].strip().upper(),
                            car_class=CarClass(data["car_class"]))
        except (KeyError, ValueError, AttributeError):
            raise ValidationError("Заполните все поля водителя корректно") from None
        if not all([driver.full_name, driver.phone, driver.car_model, driver.car_plate]):
            raise ValidationError("Поля водителя не могут быть пустыми")
        self.drivers.add(driver)
        self._commit()
        return driver

    def create_client(self, data: dict) -> Client:
        name, phone = (data.get("full_name") or "").strip(), (data.get("phone") or "").strip()
        if not name or not phone:
            raise ValidationError("ФИО и телефон обязательны")
        client = self.clients.add(Client(full_name=name, phone=phone, email=(data.get("email") or None)))
        self._commit()
        return client
