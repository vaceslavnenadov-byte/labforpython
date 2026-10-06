"""Начальные данные: администратор (из переменных окружения), машины и водители."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.models import Car, CarClass, Driver, Role, User
from src.app.security import hash_password

logger = logging.getLogger("taxi.seed")

CARS = [
    ("А101АА777", "Kia Rio", CarClass.ECONOMY, 2021),
    ("В202ВВ777", "Hyundai Solaris", CarClass.ECONOMY, 2020),
    ("Е303ЕЕ777", "Toyota Camry", CarClass.COMFORT, 2022),
    ("К404КК777", "Skoda Superb", CarClass.COMFORT, 2021),
    ("М505ММ777", "Mercedes E-class", CarClass.BUSINESS, 2023),
]
DRIVERS = [
    ("Иван Петров", "+79000000001", "77AA000001", 4.9),
    ("Олег Смирнов", "+79000000002", "77AA000002", 4.6),
    ("Анна Кузнецова", "+79000000003", "77AA000003", 4.8),
    ("Сергей Волков", "+79000000004", "77AA000004", 4.7),
    ("Мария Орлова", "+79000000005", "77AA000005", 5.0),
]


def ensure_admin(db: Session, email: str | None, password: str | None) -> None:
    """Администратор создаётся только если ADMIN_EMAIL/ADMIN_PASSWORD заданы — пароль не хранится в коде."""
    if not email or not password:
        return
    if db.scalar(select(User).where(User.email == email.lower())) is None:
        db.add(User(email=email.lower(), password_hash=hash_password(password), full_name="Диспетчер",
                    phone="+70000000000", role=Role.ADMIN))
        db.commit()
        logger.info("admin %s created", email)


def seed_fleet(db: Session) -> None:
    if db.scalar(select(Car.id).limit(1)) is not None:
        return
    for (plate, model, car_class, year), (name, phone, license_number, rating) in zip(CARS, DRIVERS, strict=True):
        car = Car(plate=plate, model=model, car_class=car_class, year=year)
        db.add(Driver(full_name=name, phone=phone, license_number=license_number, rating=rating, car=car))
    db.commit()
    logger.info("fleet seeded: %d drivers", len(DRIVERS))
