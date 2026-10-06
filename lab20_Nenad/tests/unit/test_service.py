import pytest

from src.config import load_settings
from src.models import CarClass
from src.service import calculate_cost


@pytest.mark.parametrize("car_class, km, expected", [
    (CarClass.ECONOMY, 10, 239), (CarClass.COMFORT, 10, 339), (CarClass.BUSINESS, 1, 331)])
def test_calculate_cost(car_class, km, expected):
    assert calculate_cost(car_class, km) == expected


def test_calculate_cost_rejects_non_positive_distance():
    with pytest.raises(ValueError):
        calculate_cost(CarClass.ECONOMY, 0)


def test_settings_from_environment(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_HOST", "db")
    monkeypatch.setenv("DATABASE_PASSWORD", "secret")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    settings = load_settings()
    assert settings.database_url == "postgresql+psycopg://taxi:secret@db:5432/taxi"
    assert settings.redis_url == "redis://redis:6379/0"
