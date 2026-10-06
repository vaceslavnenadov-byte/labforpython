"""Генераторы и собственный итератор."""

from models import MenuItem


def dishes_by_category(menu, category: str):
    """Генератор блюд выбранной категории."""
    for item in menu:
        if item.category.lower() == category.lower():
            yield item


def vegetarian_items(menu):
    for item in menu:
        if item.vegetarian:
            yield item


def combo_generator(menu, budget: float):
    """Лениво перебирает пары «основное блюдо + напиток» в рамках бюджета."""
    mains = [i for i in menu if i.category == "Горячее"]
    drinks = [i for i in menu if i.category == "Напитки"]
    for main in mains:
        for drink in drinks:
            total = main.final_price() + drink.final_price()
            if total <= budget:
                yield main.name, drink.name, total


class MenuPageIterator:
    """Собственный итератор: выдаёт меню страницами по page_size позиций."""

    def __init__(self, items: list[MenuItem], page_size: int):
        if page_size <= 0:
            raise ValueError("Размер страницы должен быть положительным")
        self.items = items
        self.page_size = page_size
        self.position = 0

    def __iter__(self):
        return self

    def __next__(self) -> list[MenuItem]:
        if self.position >= len(self.items):
            raise StopIteration
        page = self.items[self.position:self.position + self.page_size]
        self.position += self.page_size
        return page
