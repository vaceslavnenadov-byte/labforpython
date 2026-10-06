"""Бизнес-логика: управление меню и заказами."""

import logging

from exceptions import (
    DishAlreadyExistsError,
    DishNotFoundError,
    EmptyOrderError,
    OrderNotFoundError,
)
from models import Dish, Order, OrderItem

logger = logging.getLogger("restaurant")


class RestaurantService:
    def __init__(self, menu_repository, order_repository):
        self.menu_repository = menu_repository
        self.order_repository = order_repository
        self.menu = menu_repository.load()
        self.orders = order_repository.load()

    # ---------- Меню ----------
    def add_dish(self, name, category, price, calories):
        if self._find_dish_or_none(name):
            raise DishAlreadyExistsError(name)
        dish = Dish(name, category, price, calories)  # NegativePriceError при цене <= 0
        self.menu.append(dish)
        logger.info("Добавлено блюдо %s (%.2f руб.)", dish.name, dish.price)
        return dish

    def remove_dish(self, name):
        dish = self.find_dish(name)
        self.menu.remove(dish)
        logger.info("Удалено блюдо %s", dish.name)
        return dish

    def change_price(self, name, new_price):
        dish = self.find_dish(name)
        old_price = dish.price
        dish.price = new_price
        logger.info("Цена блюда %s изменена: %.2f -> %.2f", dish.name, old_price, dish.price)
        return dish

    def _find_dish_or_none(self, name):
        for dish in self.menu:
            if dish.name.lower() == name.strip().lower():
                return dish
        return None

    def find_dish(self, name):
        dish = self._find_dish_or_none(name)
        if dish is None:
            raise DishNotFoundError(name)
        return dish

    def search(self, text="", category=None, max_price=None):
        result = []
        for dish in self.menu:
            if text and text.lower() not in dish.name.lower():
                continue
            if category and dish.category.lower() != category.lower():
                continue
            if max_price is not None and dish.price > max_price:
                continue
            result.append(dish)
        return result

    # ---------- Заказы ----------
    def create_order(self, positions):
        """positions — список пар (название блюда, количество)."""
        if not positions:
            raise EmptyOrderError("Заказ должен содержать хотя бы одну позицию")
        number = max((order.number for order in self.orders), default=0) + 1
        order = Order(number)
        for name, quantity in positions:
            dish = self.find_dish(name)
            order.add_item(OrderItem(dish.name, dish.price, quantity))
        self.orders.append(order)
        logger.info("Создан заказ №%d на сумму %.2f", order.number, order.total)
        return order

    def find_order(self, number):
        for order in self.orders:
            if order.number == number:
                return order
        raise OrderNotFoundError(number)

    def close_order(self, number):
        order = self.find_order(number)
        order.status = "оплачен"
        return order

    # ---------- Статистика ----------
    def statistics(self):
        if not self.menu:
            return {}
        prices = [dish.price for dish in self.menu]
        return {
            "Блюд в меню": len(self.menu),
            "Средняя цена": round(sum(prices) / len(prices), 2),
            "Самое дорогое": max(self.menu, key=lambda d: d.price).name,
            "Заказов": len(self.orders),
            "Выручка": round(sum(o.total for o in self.orders), 2),
        }

    # ---------- Сохранение ----------
    def save(self):
        self.menu_repository.save(self.menu)
        self.order_repository.save(self.orders)
        logger.info("Данные сохранены")
