"""Расчёт стоимости: тариф класса × коэффициент спроса (surge)."""

from src.app.models import CarClass

TARIFFS = {  # подача, ₽/км, минимальная стоимость
    CarClass.ECONOMY: (99, 14, 199),
    CarClass.COMFORT: (149, 19, 299),
    CarClass.BUSINESS: (299, 32, 599),
}


def surge_multiplier(busy: int, total: int) -> float:
    """Чем больше водителей занято, тем выше коэффициент. Нет водителей онлайн — максимальный."""
    if total <= 0:
        return 1.5
    share = busy / total
    if share < 0.5:
        return 1.0
    if share < 0.8:
        return 1.2
    return 1.5


def calculate_price(car_class: CarClass, distance_km: float, surge: float = 1.0) -> float:
    if distance_km <= 0:
        raise ValueError("distance must be positive")
    base, per_km, minimum = TARIFFS[car_class]
    return round(max(base + per_km * distance_km, minimum) * surge, 2)
