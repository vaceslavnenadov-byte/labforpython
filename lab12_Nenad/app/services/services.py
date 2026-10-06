"""Бизнес-логика такси. Каждая публичная операция — отдельная транзакция."""

from contextlib import contextmanager
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.exceptions import BusinessRuleError, DuplicateError, NotFoundError, ValidationError
from app.models import Car, CarClass, Client, Driver, DriverStatus, Trip, TripStatus
from app.repositories.repositories import CarRepository, ClientRepository, DriverRepository, TripRepository

# Тарифы: подача + за км + за минуту
TARIFFS = {
    CarClass.ECONOMY: (99, 14, 6),
    CarClass.COMFORT: (149, 19, 8),
    CarClass.BUSINESS: (299, 32, 12),
}
NIGHT_COEFFICIENT = 1.25   # 23:00–06:00


def calculate_cost(car_class: CarClass, distance_km: float, duration_min: int, when: datetime | None = None) -> float:
    base, per_km, per_min = TARIFFS[car_class]
    cost = base + per_km * distance_km + per_min * duration_min
    hour = (when or datetime.now()).hour
    if hour >= 23 or hour < 6:
        cost *= NIGHT_COEFFICIENT
    return round(cost, 2)


class TaxiService:
    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    @contextmanager
    def transaction(self):
        """Единица работы: commit при успехе, rollback при любой ошибке."""
        session: Session = self.session_factory()
        try:
            yield session
            session.commit()
        except IntegrityError as error:
            session.rollback()
            message = str(error.orig).lower()
            if "unique" in message or "duplicate" in message:
                raise DuplicateError("Запись с таким уникальным значением уже существует") from None
            if "foreign key" in message:
                raise ValidationError("Нарушение внешнего ключа: связанная запись не существует") from None
            raise ValidationError(f"Нарушение ограничения целостности: {error.orig}") from None
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _require(entity, name: str, entity_id: int):
        if entity is None:
            raise NotFoundError(f"Объект «{name}» с id={entity_id} не найден")
        return entity

    # ---------- клиенты ----------
    def create_client(self, full_name: str, phone: str, email: str | None = None) -> Client:
        if not full_name.strip() or not phone.strip():
            raise ValidationError("ФИО и телефон обязательны")
        with self.transaction() as s:
            return ClientRepository(s).add(Client(full_name=full_name.strip(), phone=phone.strip(), email=email))

    def get_client(self, client_id: int) -> Client:
        with self.transaction() as s:
            return self._require(ClientRepository(s).get_by_id(client_id), "Клиент", client_id)

    def list_clients(self, page: int = 1, page_size: int = 10) -> list[Client]:
        with self.transaction() as s:
            return ClientRepository(s).get_all(page, page_size)

    def update_client(self, client_id: int, **fields) -> Client:
        allowed = {"full_name", "phone", "email"}
        with self.transaction() as s:
            client = self._require(ClientRepository(s).get_by_id(client_id), "Клиент", client_id)
            for key, value in fields.items():
                if key not in allowed:
                    raise ValidationError(f"Поле {key} нельзя изменить")
                setattr(client, key, value)
            return client

    def delete_client(self, client_id: int) -> None:
        with self.transaction() as s:
            client = self._require(ClientRepository(s).get_by_id(client_id), "Клиент", client_id)
            if client.trips:
                raise BusinessRuleError("Нельзя удалить клиента с историей поездок")
            ClientRepository(s).delete(client)

    def search_clients(self, text: str) -> list[Client]:
        with self.transaction() as s:
            return ClientRepository(s).search_by_name(text)

    def client_trips(self, client_id: int) -> list[Trip]:
        with self.transaction() as s:
            self._require(ClientRepository(s).get_by_id(client_id), "Клиент", client_id)
            return TripRepository(s).by_client(client_id)

    # ---------- водители и машины ----------
    def create_driver(self, full_name: str, phone: str, license_number: str, experience_years: int = 0) -> Driver:
        if experience_years < 0:
            raise ValidationError("Стаж не может быть отрицательным")
        with self.transaction() as s:
            return DriverRepository(s).add(Driver(full_name=full_name, phone=phone, license_number=license_number,
                                                  experience_years=experience_years))

    def add_car_to_driver(self, driver_id: int, plate: str, model: str, car_class: CarClass) -> Car:
        """Привязка машины к водителю (many-to-many). Машина создаётся, если её ещё нет."""
        with self.transaction() as s:
            driver = self._require(DriverRepository(s).get_by_id(driver_id), "Водитель", driver_id)
            car = CarRepository(s).get_by_plate(plate) or CarRepository(s).add(
                Car(plate=plate, model=model, car_class=car_class))
            if car not in driver.cars:
                driver.cars.append(car)
            return car

    def drivers_sorted(self, field: str = "rating", descending: bool = True) -> list[Driver]:
        if field not in ("rating", "experience", "name"):
            raise ValidationError("Сортировка возможна по rating, experience, name")
        with self.transaction() as s:
            return DriverRepository(s).sorted_by(field, descending)

    def drivers_with_cars(self) -> list[Driver]:
        with self.transaction() as s:
            return DriverRepository(s).with_cars()

    def set_driver_status(self, driver_id: int, status: DriverStatus) -> Driver:
        with self.transaction() as s:
            driver = self._require(DriverRepository(s).get_by_id(driver_id), "Водитель", driver_id)
            if driver.status == DriverStatus.BUSY:
                raise BusinessRuleError("Водитель выполняет поездку — статус меняется автоматически")
            driver.status = status
            return driver

    # ---------- поездки (транзакционные операции) ----------
    def create_trip(self, client_id: int, pickup: str, destination: str, distance_km: float,
                    duration_min: int, car_class: CarClass) -> Trip:
        """Создание поездки и назначение водителя одной транзакцией:
        1) проверить клиента; 2) найти свободного водителя с машиной класса; 3) создать поездку;
        4) пометить водителя занятым. Ошибка на любом шаге — ни одно изменение не сохранится."""
        if distance_km <= 0 or duration_min <= 0:
            raise ValidationError("Расстояние и время должны быть положительными")
        if not pickup.strip() or not destination.strip():
            raise ValidationError("Адреса не могут быть пустыми")
        with self.transaction() as s:
            self._require(ClientRepository(s).get_by_id(client_id), "Клиент", client_id)
            trip = TripRepository(s).add(Trip(
                client_id=client_id, pickup=pickup, destination=destination, distance_km=distance_km,
                duration_min=duration_min, car_class=car_class,
                cost=calculate_cost(car_class, distance_km, duration_min)))
            found = DriverRepository(s).find_free_driver(car_class)
            if found is None:
                raise BusinessRuleError(f"Нет свободных водителей класса {car_class.value}")
            driver, car = found
            trip.driver, trip.car, trip.status = driver, car, TripStatus.ASSIGNED
            driver.status = DriverStatus.BUSY
            return trip

    def start_trip(self, trip_id: int) -> Trip:
        with self.transaction() as s:
            trip = self._require(TripRepository(s).get_by_id(trip_id), "Поездка", trip_id)
            if trip.status != TripStatus.ASSIGNED:
                raise BusinessRuleError(f"Начать можно только назначенную поездку (сейчас {trip.status.value})")
            trip.status = TripStatus.IN_PROGRESS
            return trip

    def complete_trip(self, trip_id: int, actual_distance: float | None = None,
                      actual_duration: int | None = None, driver_rating: int | None = None) -> Trip:
        """Завершение: фактическая стоимость, освобождение водителя, пересчёт его рейтинга."""
        with self.transaction() as s:
            trip = self._require(TripRepository(s).get_by_id(trip_id), "Поездка", trip_id)
            if trip.status != TripStatus.IN_PROGRESS:
                raise BusinessRuleError("Завершить можно только начатую поездку")
            if actual_distance is not None:
                trip.distance_km = actual_distance
            if actual_duration is not None:
                trip.duration_min = actual_duration
            trip.cost = calculate_cost(trip.car_class, trip.distance_km, trip.duration_min, trip.created_at)
            trip.status = TripStatus.COMPLETED
            trip.finished_at = datetime.now()
            driver = trip.driver
            driver.status = DriverStatus.FREE
            if driver_rating is not None:
                if not 1 <= driver_rating <= 5:
                    raise ValidationError("Оценка должна быть от 1 до 5")
                done = sum(1 for t in driver.trips if t.status == TripStatus.COMPLETED)
                driver.rating = round((driver.rating * done + driver_rating) / (done + 1), 2)
            return trip

    def cancel_trip(self, trip_id: int) -> Trip:
        with self.transaction() as s:
            trip = self._require(TripRepository(s).get_by_id(trip_id), "Поездка", trip_id)
            if trip.status in (TripStatus.COMPLETED, TripStatus.CANCELLED):
                raise BusinessRuleError(f"Поездка уже {trip.status.value}")
            if trip.driver:
                trip.driver.status = DriverStatus.FREE
            trip.status = TripStatus.CANCELLED
            trip.cost = 0
            return trip

    def get_trip(self, trip_id: int) -> Trip:
        with self.transaction() as s:
            trip = self._require(TripRepository(s).get_by_id(trip_id), "Поездка", trip_id)
            _ = trip.client, trip.driver, trip.car   # загружаем связи до закрытия сессии
            return trip

    def filter_trips(self, **criteria) -> list[Trip]:
        with self.transaction() as s:
            return TripRepository(s).filter(**criteria)

    def statistics(self) -> dict:
        with self.transaction() as s:
            stats = TripRepository(s).statistics()
            stats["clients"] = ClientRepository(s).count()
            stats["drivers"] = DriverRepository(s).count()
            return stats
