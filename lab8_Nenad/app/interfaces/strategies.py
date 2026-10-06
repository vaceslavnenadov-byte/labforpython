from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PricingContext:
    """Параметры, от которых может зависеть цена."""
    occupancy: float = 0.0    # заполненность категории вагонов, 0..1
    days_before: int = 30     # дней до отправления


class PricingStrategy(Protocol):
    name: str

    def calculate(self, base_price: float, coefficient: float, context: PricingContext) -> float: ...
