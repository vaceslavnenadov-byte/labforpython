"""Классы предметной области: блюдо, позиция заказа, заказ."""

from datetime import datetime

from exceptions import InvalidDishDataError, NegativePriceError

CATEGORIES = ("Салаты", "Супы", "Горячее", "Десерты", "Напитки")


class Dish:
    def __init__(self, name, category, price, calories):
        self.name = name
        self.category = category
        self.price = price
        self.calories = calories

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        value = str(value).strip()
        if not value:
            raise InvalidDishDataError("Название блюда не может быть пустым")
        self._name = value

    @property
    def price(self):
        return self._price

    @price.setter
    def price(self, value):
        value = float(value)
        if value <= 0:
            raise NegativePriceError(value)
        self._price = round(value, 2)

    @property
    def calories(self):
        return self._calories

    @calories.setter
    def calories(self, value):
        value = int(value)
        if value < 0:
            raise InvalidDishDataError("Калорийность не может быть отрицательной")
        self._calories = value

    def to_dict(self):
        return {
            "name": self.name,
            "category": self.category,
            "price": self.price,
            "calories": self.calories,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data["name"], data["category"], data["price"], data["calories"])

    def __str__(self):
        return f"{self.name:<25} {self.category:<10} {self.price:>9.2f} руб. {self.calories:>5} ккал"


class OrderItem:
    """Позиция заказа. Цена фиксируется на момент заказа."""

    def __init__(self, dish_name, price, quantity):
        if quantity <= 0:
            raise InvalidDishDataError("Количество должно быть положительным")
        self.dish_name = dish_name
        self.price = float(price)
        self.quantity = int(quantity)

    @property
    def total(self):
        return round(self.price * self.quantity, 2)

    def to_dict(self):
        return {"dish_name": self.dish_name, "price": self.price, "quantity": self.quantity}

    @classmethod
    def from_dict(cls, data):
        return cls(data["dish_name"], data["price"], data["quantity"])


class Order:
    def __init__(self, number, items=None, created_at=None, status="новый"):
        self.number = number
        self.items = items or []
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M")
        self.status = status

    @property
    def total(self):
        return round(sum(item.total for item in self.items), 2)

    def add_item(self, item):
        for existing in self.items:
            if existing.dish_name == item.dish_name:
                existing.quantity += item.quantity
                return
        self.items.append(item)

    def to_dict(self):
        return {
            "number": self.number,
            "created_at": self.created_at,
            "status": self.status,
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data):
        items = [OrderItem.from_dict(item) for item in data["items"]]
        return cls(data["number"], items, data["created_at"], data["status"])

    def __str__(self):
        lines = [f"Заказ №{self.number} от {self.created_at} [{self.status}]"]
        for item in self.items:
            lines.append(f"   {item.dish_name} × {item.quantity} = {item.total:.2f} руб.")
        lines.append(f"   Итого: {self.total:.2f} руб.")
        return "\n".join(lines)
