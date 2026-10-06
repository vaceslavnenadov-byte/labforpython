"""Сохранение и загрузка данных: JSON-репозиторий, экспорт/импорт CSV, резервные копии."""

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path

from exceptions import StorageError
from models import Dish, Order

DATA_DIR = Path(__file__).parent / "data"


class JsonRepository:
    """Репозиторий объектов в JSON-файле (доп. задание №8).

    model_class должен иметь методы to_dict() и from_dict().
    """

    def __init__(self, path, model_class):
        self.path = Path(path)
        self.model_class = model_class

    def load(self):
        if not self.path.exists():
            return []  # первый запуск — файла ещё нет
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                raw = json.load(file)
            return [self.model_class.from_dict(item) for item in raw]
        except json.JSONDecodeError as error:
            raise StorageError(f"Файл {self.path.name} повреждён: {error}") from error
        except (KeyError, TypeError, ValueError) as error:
            raise StorageError(f"Файл {self.path.name} содержит некорректные данные: {error}") from error

    def save(self, objects):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.backup()
        try:
            with open(self.path, "w", encoding="utf-8") as file:
                json.dump([obj.to_dict() for obj in objects], file, ensure_ascii=False, indent=4)
        except OSError as error:
            raise StorageError(f"Не удалось записать {self.path}: {error}") from error

    def backup(self):
        """Резервная копия перед перезаписью (доп. задание №2)."""
        if self.path.exists():
            backup_dir = self.path.parent / "backup"
            backup_dir.mkdir(exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy(self.path, backup_dir / f"{self.path.stem}_{stamp}.json")


def export_menu_csv(dishes, path=DATA_DIR / "menu.csv"):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["name", "category", "price", "calories"])
        writer.writeheader()
        for dish in dishes:
            writer.writerow(dish.to_dict())
    return path


def export_orders_csv(orders, path=DATA_DIR / "orders.csv"):
    """Вложенные позиции заказа записываются в упрощённом виде одной строкой."""
    path = Path(path)
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["number", "created_at", "status", "items", "total"])
        for order in orders:
            items = "; ".join(f"{i.dish_name} x{i.quantity}" for i in order.items)
            writer.writerow([order.number, order.created_at, order.status, items, order.total])
    return path


def import_menu_csv(path):
    """Импорт меню из CSV (доп. задание №3). Возвращает (блюда, ошибки)."""
    dishes, errors = [], []
    try:
        with open(path, "r", encoding="utf-8") as file:
            for line_number, row in enumerate(csv.DictReader(file), start=2):
                try:
                    dishes.append(Dish.from_dict(row))
                except Exception as error:  # строка пропускается, остальные загружаются
                    errors.append(f"строка {line_number}: {error}")
    except FileNotFoundError as error:
        raise StorageError(f"Файл {path} не найден") from error
    return dishes, errors
