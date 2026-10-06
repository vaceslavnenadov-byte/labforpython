"""Функции высшего порядка для обработки коллекций позиций меню."""

from functools import reduce
from typing import Callable, Iterable

from models import MenuItem


# ---------- Универсальные функции высшего порядка ----------

def filter_objects(objects: Iterable, predicate: Callable) -> list:
    return list(filter(predicate, objects))


def transform_objects(objects: Iterable, operation: Callable) -> list:
    return list(map(operation, objects))


def sort_objects(objects: Iterable, key_function: Callable, reverse: bool = False) -> list:
    return sorted(objects, key=key_function, reverse=reverse)


def aggregate(objects: Iterable, operation: Callable, initial):
    return reduce(operation, objects, initial)


def make_calorie_filter(max_calories: int) -> Callable[[MenuItem], bool]:
    """Функция, возвращающая функцию (замыкание-предикат)."""
    return lambda item: item.calories <= max_calories


def make_discount(percent: float) -> Callable[[MenuItem], tuple]:
    """Возвращает функцию расчёта цены со скидкой."""
    def apply(item: MenuItem) -> tuple:
        return item.name, round(item.final_price() * (1 - percent / 100), 2)
    return apply


# ---------- Операции варианта 10 ----------

def filter_by_calories(menu, max_calories):
    return filter_objects(menu, make_calorie_filter(max_calories))


def get_prices(menu) -> list[float]:
    return transform_objects(menu, lambda item: item.final_price())


def sort_by_price(menu, reverse=False):
    return sort_objects(menu, lambda item: item.final_price(), reverse)


def average_calories(menu) -> float:
    if not menu:
        raise ValueError("Меню пустое — среднюю калорийность вычислить нельзя")
    total = aggregate(menu, lambda acc, item: acc + item.calories, 0)
    return total / len(menu)


def has_vegetarian(menu) -> bool:
    return any(item.vegetarian for item in menu)


def all_cheaper_than(menu, limit) -> bool:
    return all(item.final_price() < limit for item in menu)


def calories_by_category(menu) -> dict[str, float]:
    """dict comprehension + set comprehension."""
    categories = {item.category for item in menu}
    return {
        category: round(average_calories([i for i in menu if i.category == category]), 1)
        for category in sorted(categories)
    }


def most_expensive(menu):
    return reduce(lambda a, b: a if a.final_price() >= b.final_price() else b, menu)


# ---------- Конвейер (доп. задание) ----------

def process(objects, predicate, transform, key_function, reverse=False):
    """Исходные объекты → filter → map → sorted → генератор результата.

    filter и map ленивые: промежуточные списки не создаются, список
    появляется только в sorted (сортировка требует всех элементов).
    """
    filtered = filter(predicate, objects)
    transformed = map(transform, filtered)
    for value in sorted(transformed, key=key_function, reverse=reverse):
        yield value
