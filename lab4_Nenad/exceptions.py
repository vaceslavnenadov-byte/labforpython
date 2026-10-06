"""Пользовательские исключения системы управления рестораном."""


class RestaurantError(Exception):
    """Базовое исключение предметной области."""


class NegativePriceError(RestaurantError):
    """Попытка установить блюду отрицательную (или нулевую) цену."""

    def __init__(self, price):
        super().__init__(f"Цена блюда должна быть положительной, получено: {price}")
        self.price = price


class InvalidDishDataError(RestaurantError):
    """Некорректные данные блюда (пустое название, отрицательная калорийность и т. п.)."""


class DishNotFoundError(RestaurantError):
    def __init__(self, name):
        super().__init__(f"Блюдо «{name}» не найдено в меню")


class DishAlreadyExistsError(RestaurantError):
    def __init__(self, name):
        super().__init__(f"Блюдо «{name}» уже есть в меню")


class OrderNotFoundError(RestaurantError):
    def __init__(self, number):
        super().__init__(f"Заказ №{number} не найден")


class EmptyOrderError(RestaurantError):
    """Попытка оформить заказ без позиций."""


class StorageError(RestaurantError):
    """Ошибка чтения/записи файлов данных."""
