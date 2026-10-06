"""Strategy: алгоритмы расчёта стоимости билета."""

from interfaces.strategies import PricingContext


class StandardPricing:
    name = "стандартный"

    def calculate(self, base_price: float, coefficient: float, context: PricingContext) -> float:
        return round(base_price * coefficient, 2)


class ConcessionPricing:
    """Льготный тариф (студенты, пенсионеры): скидка 50%."""
    name = "льготный"
    DISCOUNT = 0.5

    def calculate(self, base_price: float, coefficient: float, context: PricingContext) -> float:
        return round(base_price * coefficient * (1 - self.DISCOUNT), 2)


class DynamicPricing:
    """Динамический тариф: цена растёт с заполненностью и близостью отправления,
    ранняя покупка (за 45+ дней) даёт скидку 15%."""
    name = "динамический"

    def calculate(self, base_price: float, coefficient: float, context: PricingContext) -> float:
        price = base_price * coefficient * (1 + 0.5 * context.occupancy)
        if context.days_before < 3:
            price *= 1.2
        elif context.days_before >= 45:
            price *= 0.85
        return round(price, 2)
