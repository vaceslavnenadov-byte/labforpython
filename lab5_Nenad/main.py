"""
Лабораторная работа №5. Функции высшего порядка, итераторы и генераторы.
Вариант 10. Ресторан.

Запуск: python main.py
"""

import sys

from generators import MenuPageIterator, combo_generator, dishes_by_category, vegetarian_items
from models import Dessert, Dish, Drink, create_menu
from operations import (
    all_cheaper_than,
    average_calories,
    calories_by_category,
    filter_by_calories,
    get_prices,
    has_vegetarian,
    make_discount,
    most_expensive,
    process,
    sort_by_price,
    transform_objects,
)


def show(items, title):
    print(f"\n{title}:")
    if not items:
        print("  (пусто)")
    for item in items:
        print("  ", item)


def read_number(prompt, cast=float):
    while True:
        try:
            value = cast(input(prompt).replace(",", "."))
            if value < 0:
                raise ValueError
            return value
        except ValueError:
            print("  Ошибка: введите неотрицательное число.")


def demo_generator(menu):
    category = input("Категория (Салаты, Супы, Горячее, Десерты, Напитки): ").strip()
    gen = dishes_by_category(menu, category)
    print("Получаем элементы через next():")
    try:
        print("  next ->", next(gen))
        print("  next ->", next(gen))
        print("  остальные в цикле for:")
        for item in gen:
            print("   ", item)
        next(gen)
    except StopIteration:
        print("  StopIteration: элементы генератора закончились.")


def demo_iterator(menu):
    size = read_number("Позиций на странице: ", int)
    try:
        pages = MenuPageIterator(menu, size)
    except ValueError as error:
        print("Ошибка:", error)
        return
    for number, page in enumerate(pages, start=1):
        print(f"--- Страница {number} ---")
        for item in page:
            print("  ", item)
    try:
        next(pages)
    except StopIteration:
        print("Итератор исчерпан (StopIteration).")


def demo_lazy():
    list_result = [x * x for x in range(1_000_000)]
    generator_result = (x * x for x in range(1_000_000))
    print(f"Список из 1 000 000 квадратов: {sys.getsizeof(list_result):>10,} байт".replace(",", " "))
    print(f"Генераторное выражение:        {sys.getsizeof(generator_result):>10,} байт".replace(",", " "))
    print("Список вычисляет и хранит все значения сразу при создании.")
    print("Генератор хранит только своё состояние и вычисляет значение при запросе:")
    print("  первые три:", next(generator_result), next(generator_result), next(generator_result))


def demo_pipeline(menu):
    print("Конвейер 1: вегетарианские → (название, цена со скидкой 10%) → по цене")
    for name, price in process(menu, lambda i: i.vegetarian, make_discount(10), lambda p: p[1]):
        print(f"  {name:<22} {price:>8.2f}")
    print("Конвейер 2: калорийность > 300 → (название, ккал) → по убыванию ккал")
    for name, kcal in process(menu, lambda i: i.calories > 300, lambda i: (i.name, i.calories),
                              lambda p: p[1], reverse=True):
        print(f"  {name:<22} {kcal:>5}")


def add_item(menu):
    print("1 — блюдо, 2 — десерт, 3 — напиток")
    kind = input("Тип: ").strip()
    name = input("Название: ")
    price = read_number("Цена: ")
    calories = read_number("Калорийность: ", int)
    try:
        if kind == "1":
            item = Dish(name, input("Категория: ").strip(), price, calories,
                        read_number("Вес, г: ", int), input("Вегетарианское? (д/н): ") == "д")
        elif kind == "2":
            item = Dessert(name, price, calories, read_number("Вес, г: ", int))
        elif kind == "3":
            item = Drink(name, price, calories, read_number("Объём, мл: ", int))
        else:
            print("Неизвестный тип.")
            return
    except ValueError as error:
        print("Ошибка:", error)
        return
    menu.append(item)
    print("Добавлено:", item)


def main():
    menu = create_menu()
    while True:
        print("\n===== РЕСТОРАН: ФУНКЦИОНАЛЬНАЯ ОБРАБОТКА =====")
        print("1. Показать меню")
        print("2. Фильтрация по калорийности (filter)")
        print("3. Список цен (map)")
        print("4. Сортировка по цене (sorted + key)")
        print("5. Статистика (reduce, comprehensions)")
        print("6. Проверки any()/all()")
        print("7. Генератор блюд категории (next, StopIteration)")
        print("8. Собственный итератор (постраничный вывод)")
        print("9. Ленивые вычисления: список vs генератор")
        print("10. Конвейер обработки")
        print("11. Комбо в рамках бюджета (генератор)")
        print("12. Добавить позицию")
        print("0. Выход")
        choice = input("Выберите действие: ").strip()

        if choice == "1":
            show(menu, "Меню")
        elif choice == "2":
            limit = read_number("Максимальная калорийность: ", int)
            show(filter_by_calories(menu, limit), f"Позиции до {limit} ккал")
        elif choice == "3":
            names = transform_objects(menu, lambda i: i.name)
            for name, price in zip(names, get_prices(menu)):
                print(f"  {name:<22} {price:>8.2f}")
        elif choice == "4":
            desc = input("По убыванию? (д/н): ").strip().lower() == "д"
            show(sort_by_price(menu, desc), "Меню, отсортированное по цене")
        elif choice == "5":
            try:
                print(f"Средняя калорийность: {average_calories(menu):.1f} ккал")
                print("Средняя калорийность по категориям:", calories_by_category(menu))
                print("Самая дорогая позиция:", most_expensive(menu).name)
                print("Суммарная стоимость меню:", round(sum(get_prices(menu)), 2))
            except (ValueError, TypeError) as error:
                print("Ошибка:", error)
        elif choice == "6":
            print("Есть вегетарианские блюда (any):", "да" if has_vegetarian(menu) else "нет")
            show(list(vegetarian_items(menu)), "Вегетарианские позиции")
            limit = read_number("Проверить, что все позиции дешевле: ")
            print("Все позиции дешевле (all):", "да" if all_cheaper_than(menu, limit) else "нет")
        elif choice == "7":
            demo_generator(menu)
        elif choice == "8":
            demo_iterator(menu)
        elif choice == "9":
            demo_lazy()
        elif choice == "10":
            demo_pipeline(menu)
        elif choice == "11":
            budget = read_number("Бюджет, руб.: ")
            combos = combo_generator(menu, budget)
            found = False
            for main_dish, drink, total in combos:
                found = True
                print(f"  {main_dish} + {drink} = {total:.2f}")
            if not found:
                print("  Нет вариантов в рамках бюджета.")
        elif choice == "12":
            add_item(menu)
        elif choice == "0":
            break
        else:
            print("Неизвестный пункт меню.")


if __name__ == "__main__":
    main()
