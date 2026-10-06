"""Factory + Strategy (доп. задание №2): стратегия создаётся по названию."""

from interfaces.strategies import PricingStrategy
from strategies.pricing import ConcessionPricing, DynamicPricing, StandardPricing


class StrategyFactory:
    _strategies = {
        "standard": StandardPricing,
        "concession": ConcessionPricing,
        "dynamic": DynamicPricing,
    }

    @classmethod
    def available(cls) -> list[str]:
        return list(cls._strategies)

    @classmethod
    def create(cls, name: str) -> PricingStrategy:
        try:
            return cls._strategies[name]()
        except KeyError:
            raise ValueError(f"Неизвестный тариф: {name}") from None
