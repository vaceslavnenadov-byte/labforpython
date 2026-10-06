"""Проверка пользовательского ввода (отдельно от Telegram — легко тестировать)."""

import re


class InputError(ValueError):
    pass


def validate_city(text: str | None) -> str:
    if not text or not text.strip():
        raise InputError("Название города не может быть пустым.")
    text = text.strip()
    if len(text) < 2 or not re.fullmatch(r"[А-Яа-яЁёA-Za-z\- ]+", text):
        raise InputError("Город — это слово из букв, например «Москва».")
    return text[0].upper() + text[1:]


def validate_seat(text: str | None, capacity: int) -> int:
    if text is None or not text.strip().isdigit():
        raise InputError("Номер места нужно ввести числом, например 12.")
    seat = int(text)
    if not 1 <= seat <= capacity:
        raise InputError(f"В вагоне места с 1 по {capacity}.")
    return seat


def validate_passenger_name(text: str | None) -> str:
    if not text or not text.strip():
        raise InputError("ФИО не может быть пустым.")
    parts = text.split()
    if len(parts) < 2:
        raise InputError("Введите фамилию и имя через пробел.")
    if not all(re.fullmatch(r"[А-Яа-яЁёA-Za-z\-]+", p) for p in parts):
        raise InputError("ФИО может содержать только буквы и дефис.")
    return " ".join(p.capitalize() for p in parts)
