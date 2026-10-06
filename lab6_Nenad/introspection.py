"""Интроспекция объектов."""

import inspect
from dataclasses import fields, is_dataclass

from models import Entity


def inspect_object(obj) -> None:
    cls = type(obj)
    print("=== ИНФОРМАЦИЯ ОБ ОБЪЕКТЕ ===")
    print("Тип:", cls.__name__)
    print("Модуль:", cls.__module__)
    print("Это Entity (isinstance):", isinstance(obj, Entity))
    print("Класс наследует Entity (issubclass):", issubclass(cls, Entity))
    print("Родительские классы:", " -> ".join(c.__name__ for c in cls.__mro__))
    if hasattr(obj, "id"):
        print("ID:", getattr(obj, "id"))

    print("Атрибуты:")
    if is_dataclass(obj):
        for f in fields(obj):
            value = getattr(obj, f.name)
            if isinstance(value, list):
                value = f"список из {len(value)} элементов"
            print(f"   {f.name}: {f.type if isinstance(f.type, str) else f.type.__name__} = {value}")

    print("Методы:")
    for name, member in inspect.getmembers(cls, inspect.isfunction):
        if not name.startswith("_"):
            print(f"   {name}{inspect.signature(member)}")

    public = [name for name in dir(obj) if not name.startswith("_")]
    print(f"Всего публичных имён (dir): {len(public)}")


def safe_set(obj, attribute: str, value) -> bool:
    """Пример setattr: изменение атрибута только если он существует."""
    if not hasattr(obj, attribute):
        return False
    setattr(obj, attribute, value)
    return True
