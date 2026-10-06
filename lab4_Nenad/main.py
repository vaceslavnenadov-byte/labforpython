"""
Лабораторная работа №4. Модули, исключения, файлы и сериализация данных.
Вариант 10. Ресторан — система управления меню и заказами.

Запуск:  python main.py
Данные сохраняются в data/menu.json и data/orders.json и
автоматически загружаются при следующем запуске.
"""

import logging

from exceptions import NegativePriceError, RestaurantError, StorageError
from models import CATEGORIES, Dish, Order
from services import RestaurantService
from storage import DATA_DIR, JsonRepository, export_menu_csv, export_orders_csv, import_menu_csv

DEFAULT_MENU = [
    ("Цезарь с курицей", "Салаты", 420, 380),
    ("Греческий", "Салаты", 350, 240),
    ("Борщ", "Супы", 290, 310),
    ("Том ям", "Супы", 520, 280),
    ("Стейк рибай", "Горячее", 1650, 720),
    ("Паста карбонара", "Горячее", 590, 640),
    ("Тирамису", "Десерты", 380, 450),
    ("Морс клюквенный", "Напитки", 150, 90),
]


def setup_logging():
    DATA_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=DATA_DIR / "operations.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )


def read_float(prompt):
    while True:
        try:
            return float(input(prompt).replace(",", "."))
        except ValueError:
            print("  Ошибка: необходимо ввести число.")


def read_int(prompt):
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("  Ошибка: необходимо ввести целое число.")


def print_dishes(dishes):
    if not dishes:
        print("  Нет блюд.")
    for dish in dishes:
        print("  " + str(dish))


def create_service():
    service = RestaurantService(
        JsonRepository(DATA_DIR / "menu.json", Dish),
        JsonRepository(DATA_DIR / "orders.json", Order),
    )
    if not service.menu:
        print("Файл меню не найден — загружено меню по умолчанию.")
        for data in DEFAULT_MENU:
            service.add_dish(*data)
    else:
        print(f"Загружено блюд: {len(service.menu)}, заказов: {len(service.orders)}.")
    return service


def order_dialog(service):
    positions = []
    print("Вводите блюда заказа. Пустое название — завершить.")
    while True:
        name = input("  Блюдо: ").strip()
        if not name:
            break
        try:
            service.find_dish(name)  # проверяем сразу, чтобы сообщить об ошибке
        except RestaurantError as error:
            print("  " + str(error))
            continue
        quantity = read_int("  Количество: ")
        if quantity <= 0:
            print("  Количество должно быть положительным.")
            continue
        positions.append((name, quantity))
    return service.create_order(positions)


def main():
    setup_logging()
    try:
        service = create_service()
    except StorageError as error:
        print("Ошибка загрузки данных:", error)
        print("Работа продолжается с пустым меню.")
        service = RestaurantService(
            JsonRepository(DATA_DIR / "menu_new.json", Dish),
            JsonRepository(DATA_DIR / "orders_new.json", Order),
        )

    while True:
        print("\n===== РЕСТОРАН: МЕНЮ ПРОГРАММЫ =====")
        print("1. Показать меню")
        print("2. Добавить блюдо")
        print("3. Удалить блюдо")
        print("4. Изменить цену")
        print("5. Поиск блюд")
        print("6. Создать заказ")
        print("7. Показать заказы")
        print("8. Статистика")
        print("9. Сохранить JSON")
        print("10. Экспорт в CSV")
        print("11. Импорт меню из CSV")
        print("0. Сохранить и выйти")
        choice = input("Выберите действие: ").strip()
        try:
            if choice == "1":
                print_dishes(service.menu)
            elif choice == "2":
                print("Категории:", ", ".join(CATEGORIES))
                dish = service.add_dish(
                    input("Название: "), input("Категория: "),
                    read_float("Цена: "), read_int("Калорийность: "),
                )
                print("Добавлено:", dish)
            elif choice == "3":
                print("Удалено:", service.remove_dish(input("Название: ")).name)
            elif choice == "4":
                dish = service.change_price(input("Название: "), read_float("Новая цена: "))
                print("Изменено:", dish)
            elif choice == "5":
                text = input("Часть названия (Enter — любое): ")
                category = input("Категория (Enter — любая): ").strip() or None
                limit = input("Максимальная цена (Enter — любая): ").strip()
                print_dishes(service.search(text, category, float(limit) if limit else None))
            elif choice == "6":
                print(order_dialog(service))
            elif choice == "7":
                for order in service.orders:
                    print(order)
                if not service.orders:
                    print("  Заказов нет.")
            elif choice == "8":
                for key, value in service.statistics().items():
                    print(f"  {key}: {value}")
            elif choice == "9":
                service.save()
                print("Сохранено в", DATA_DIR)
            elif choice == "10":
                print("Меню:", export_menu_csv(service.menu))
                print("Заказы:", export_orders_csv(service.orders))
            elif choice == "11":
                dishes, errors = import_menu_csv(input("Путь к CSV: ").strip())
                added = 0
                for dish in dishes:
                    try:
                        service.add_dish(dish.name, dish.category, dish.price, dish.calories)
                        added += 1
                    except RestaurantError as error:
                        errors.append(str(error))
                print(f"Импортировано: {added}")
                for error in errors:
                    print("  Пропущено:", error)
            elif choice == "0":
                service.save()
                print("Данные сохранены. До свидания!")
                break
            else:
                print("Неизвестный пункт меню.")
        except NegativePriceError as error:
            print("Ошибка цены:", error)
        except RestaurantError as error:
            print("Ошибка:", error)
        except ValueError:
            print("Ошибка: некорректное число.")


if __name__ == "__main__":
    main()
