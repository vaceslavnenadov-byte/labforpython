"""Классы предметной области: позиции меню ресторана."""

from abc import ABC, abstractmethod


class MenuItem(ABC):
    """Базовый класс позиции меню."""

    def __init__(self, name: str, category: str, price: float, calories: int, vegetarian: bool = False):
        if not name.strip():
            raise ValueError("Название не может быть пустым")
        if price <= 0:
            raise ValueError(f"Цена должна быть положительной: {price}")
        if calories < 0:
            raise ValueError(f"Калорийность не может быть отрицательной: {calories}")
        self.name = name
        self.category = category
        self.price = float(price)
        self.calories = int(calories)
        self.vegetarian = vegetarian

    @abstractmethod
    def kind(self) -> str:
        """Тип позиции."""

    def final_price(self) -> float:
        """Цена для гостя (может переопределяться)."""
        return self.price

    def __repr__(self):
        veg = " 🌱" if self.vegetarian else ""
        return (f"{self.kind():<8} {self.name:<22} {self.category:<9} "
                f"{self.final_price():>8.2f} руб. {self.calories:>4} ккал{veg}")


class Dish(MenuItem):
    """Блюдо кухни. Для блюд хранится вес порции."""

    def __init__(self, name, category, price, calories, weight, vegetarian=False):
        super().__init__(name, category, price, calories, vegetarian)
        self.weight = weight

    def kind(self):
        return "Блюдо"


class Drink(MenuItem):
    """Напиток. Алкогольные напитки облагаются наценкой 20%."""

    def __init__(self, name, price, calories, volume, alcoholic=False):
        super().__init__(name, "Напитки", price, calories, vegetarian=True)
        self.volume = volume
        self.alcoholic = alcoholic

    def kind(self):
        return "Напиток"

    def final_price(self):
        return round(self.price * 1.2, 2) if self.alcoholic else self.price


class Dessert(Dish):
    """Десерт — блюдо с признаком содержания сахара."""

    def __init__(self, name, price, calories, weight, sugar_free=False):
        super().__init__(name, "Десерты", price, calories, weight, vegetarian=True)
        self.sugar_free = sugar_free

    def kind(self):
        return "Десерт"


def create_menu() -> list[MenuItem]:
    return [
        Dish("Цезарь с курицей", "Салаты", 420, 380, 250),
        Dish("Греческий салат", "Салаты", 350, 240, 230, vegetarian=True),
        Dish("Борщ", "Супы", 290, 310, 350),
        Dish("Крем-суп грибной", "Супы", 330, 260, 300, vegetarian=True),
        Dish("Стейк рибай", "Горячее", 1650, 720, 300),
        Dish("Паста карбонара", "Горячее", 590, 640, 320),
        Dish("Ризотто с овощами", "Горячее", 520, 480, 300, vegetarian=True),
        Dessert("Тирамису", 380, 450, 150),
        Dessert("Фруктовый сорбет", 260, 120, 120, sugar_free=True),
        Drink("Морс клюквенный", 150, 90, 300),
        Drink("Капучино", 210, 120, 250),
        Drink("Бокал вина", 450, 85, 150, alcoholic=True),
    ]
