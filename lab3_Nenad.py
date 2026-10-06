"""
Лабораторная работа №3. Объектно-ориентированное программирование в Python.
Вариант 10. Система доставки.

Классы:
    Address, Parcel               — вспомогательные (композиция);
    Delivery (ABC)                — базовый класс доставки;
    CourierDelivery               — курьерская доставка;
    ExpressCourierDelivery        — срочная курьерская (ещё один уровень наследования);
    PostDelivery                  — почтовая доставка;
    DeliveryService               — служба доставки, содержит коллекцию доставок.

Каждый тип доставки рассчитывает стоимость по собственной формуле
(полиморфный метод calculate_cost()).
"""

from abc import ABC, abstractmethod


# ============================================================
# Объекты, входящие в состав доставки (композиция)
# ============================================================

class Address:
    def __init__(self, city, street):
        self.city = city
        self.street = street

    def __str__(self):
        return f"г. {self.city}, {self.street}"


class Parcel:
    """Посылка. Вес защищён свойством."""

    def __init__(self, description, weight):
        self.description = description
        self.weight = weight

    @property
    def weight(self):
        return self._weight

    @weight.setter
    def weight(self, value):
        if value <= 0:
            raise ValueError("Вес посылки должен быть положительным")
        if value > 1000:
            raise ValueError("Вес посылки не может превышать 1000 кг")
        self._weight = float(value)

    def __str__(self):
        return f"{self.description} ({self._weight} кг)"


# ============================================================
# Базовый абстрактный класс
# ============================================================

class Delivery(ABC):
    STATUSES = ("создана", "в пути", "доставлена", "отменена")
    _next_number = 1          # атрибут класса — общий счётчик номеров

    def __init__(self, sender, recipient, parcel, distance):
        self._number = Delivery._next_number
        Delivery._next_number += 1
        self.sender = sender            # композиция: Address
        self.recipient = recipient      # композиция: Address
        self.parcel = parcel            # композиция: Parcel
        self.distance = distance        # через property
        self._status = "создана"

    # ----- свойства (инкапсуляция) -----
    @property
    def number(self):
        return self._number

    @property
    def status(self):
        return self._status

    @property
    def distance(self):
        return self._distance

    @distance.setter
    def distance(self, value):
        if value <= 0:
            raise ValueError("Расстояние должно быть положительным")
        self._distance = float(value)

    # ----- абстрактные методы -----
    @abstractmethod
    def calculate_cost(self):
        """Стоимость доставки, руб."""

    @abstractmethod
    def estimate_days(self):
        """Ориентировочный срок доставки, дней."""

    # ----- общие методы -----
    def type_name(self):
        return "Доставка"

    def start(self):
        if self._status != "создана":
            raise ValueError(f"Нельзя отправить доставку в статусе «{self._status}»")
        self._status = "в пути"

    def complete(self):
        if self._status != "в пути":
            raise ValueError("Завершить можно только доставку, находящуюся в пути")
        self._status = "доставлена"

    def cancel(self):
        if self._status == "доставлена":
            raise ValueError("Нельзя отменить уже выполненную доставку")
        self._status = "отменена"

    def get_info(self):
        return (f"№{self._number} [{self.type_name()}] {self.parcel}: "
                f"{self.sender} → {self.recipient}, {self._distance:g} км, "
                f"{self.calculate_cost():.2f} руб., ~{self.estimate_days()} дн., "
                f"статус: {self._status}")

    # ----- перегрузка операторов -----
    def __eq__(self, other):
        return isinstance(other, Delivery) and self.calculate_cost() == other.calculate_cost()

    def __lt__(self, other):
        return self.calculate_cost() < other.calculate_cost()

    def __str__(self):
        return self.get_info()


# ============================================================
# Производные классы
# ============================================================

class CourierDelivery(Delivery):
    """Курьер: 150 руб. подача + 25 руб./км + 20 руб./кг, +200 руб. за подъём на этаж."""

    BASE = 150
    PER_KM = 25
    PER_KG = 20

    def __init__(self, sender, recipient, parcel, distance, to_door=True):
        super().__init__(sender, recipient, parcel, distance)
        self.to_door = to_door

    def type_name(self):
        return "Курьер"

    def calculate_cost(self):
        cost = self.BASE + self.distance * self.PER_KM + self.parcel.weight * self.PER_KG
        if self.to_door:
            cost += 200
        return round(cost, 2)

    def estimate_days(self):
        return 1 if self.distance <= 50 else 2


class ExpressCourierDelivery(CourierDelivery):
    """Срочный курьер: стоимость обычного курьера × 1.8, доставка в день заказа."""

    MULTIPLIER = 1.8

    def type_name(self):
        return "Экспресс-курьер"

    def calculate_cost(self):
        return round(super().calculate_cost() * self.MULTIPLIER, 2)

    def estimate_days(self):
        return 0 if self.distance <= 100 else 1


class PostDelivery(Delivery):
    """Почта: тариф по весовым ступеням + 2 руб./км, объявленная ценность 3%."""

    def __init__(self, sender, recipient, parcel, distance, declared_value=0):
        super().__init__(sender, recipient, parcel, distance)
        if declared_value < 0:
            raise ValueError("Объявленная ценность не может быть отрицательной")
        self.declared_value = declared_value

    def type_name(self):
        return "Почта"

    def weight_tariff(self):
        weight = self.parcel.weight
        if weight <= 1:
            return 250
        elif weight <= 5:
            return 400
        elif weight <= 20:
            return 700
        return 700 + (weight - 20) * 30

    def calculate_cost(self):
        return round(self.weight_tariff() + self.distance * 2 + self.declared_value * 0.03, 2)

    def estimate_days(self):
        return 3 + int(self.distance // 500)


# ============================================================
# Служба доставки (композиция + собственный итератор)
# ============================================================

class DeliveryService:
    def __init__(self, name):
        self.name = name
        self._deliveries = []

    def add(self, delivery):
        if not isinstance(delivery, Delivery):
            raise TypeError("Можно добавить только объект Delivery")
        self._deliveries.append(delivery)

    def remove(self, number):
        delivery = self.find(number)
        self._deliveries.remove(delivery)
        return delivery

    def find(self, number):
        for delivery in self._deliveries:
            if delivery.number == number:
                return delivery
        raise LookupError(f"Доставка №{number} не найдена")

    def search(self, city=None, status=None, max_cost=None):
        """Поиск по нескольким параметрам."""
        result = []
        for d in self._deliveries:
            if city and city.lower() not in d.recipient.city.lower():
                continue
            if status and d.status != status:
                continue
            if max_cost is not None and d.calculate_cost() > max_cost:
                continue
            result.append(d)
        return result

    def sorted_by_cost(self, reverse=False):
        return sorted(self._deliveries, reverse=reverse)   # используется __lt__

    def total_revenue(self):
        return sum(d.calculate_cost() for d in self._deliveries if d.status != "отменена")

    def statistics(self):
        stats = {}
        for d in self._deliveries:
            key = d.type_name()
            count, total = stats.get(key, (0, 0))
            stats[key] = (count + 1, total + d.calculate_cost())
        return stats

    def all(self):
        return list(self._deliveries)

    def __len__(self):
        return len(self._deliveries)

    def __iter__(self):
        return DeliveryIterator(self._deliveries)


class DeliveryIterator:
    """Собственный итератор: перебирает только активные (не отменённые) доставки."""

    def __init__(self, deliveries):
        self._deliveries = deliveries
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        while self._index < len(self._deliveries):
            delivery = self._deliveries[self._index]
            self._index += 1
            if delivery.status != "отменена":
                return delivery
        raise StopIteration


# ============================================================
# Демонстрация и меню
# ============================================================

def create_demo_service():
    service = DeliveryService("БыстроДоставка")
    moscow = Address("Москва", "ул. Тверская, 1")
    service.add(CourierDelivery(moscow, Address("Москва", "ул. Арбат, 10"), Parcel("Документы", 0.5), 12))
    service.add(PostDelivery(moscow, Address("Казань", "ул. Баумана, 5"), Parcel("Книги", 4), 820, 3000))
    service.add(ExpressCourierDelivery(moscow, Address("Химки", "ул. Ленина, 3"), Parcel("Ноутбук", 2.5), 30))
    service.add(PostDelivery(moscow, Address("Новосибирск", "Красный пр., 50"), Parcel("Посуда", 12), 3300))
    service.add(CourierDelivery(moscow, Address("Москва", "ул. Лесная, 7"), Parcel("Цветы", 1), 8, to_door=False))
    return service


def run_tests(service):
    """Демонстрация требований раздела «Тестирование»."""
    print("\n--- Тест 1. Объекты каждого типа ---")
    for d in service:
        print(" ", type(d).__name__)

    print("\n--- Тест 2/3/6. Полиморфный вызов calculate_cost() ---")
    for d in service:
        print(f"  {d.type_name():<16} {d.calculate_cost():>10.2f} руб.")

    print("\n--- Тест 4. Изменение состояния ---")
    first = service.find(1)
    first.start()
    first.complete()
    print(" ", first.get_info())

    print("\n--- Тест 5. Некорректное значение свойства ---")
    try:
        first.distance = -10
    except ValueError as error:
        print("  Ошибка перехвачена:", error)
    try:
        Parcel("Камень", 0)
    except ValueError as error:
        print("  Ошибка перехвачена:", error)

    print("\n--- Тест 7. Композиция ---")
    print(f"  Получатель доставки №1: {first.recipient}, посылка: {first.parcel}")
    print(f"  В службе «{service.name}» доставок: {len(service)}")


def read_number(prompt, cast=float):
    while True:
        try:
            return cast(input(prompt).replace(",", "."))
        except ValueError:
            print("  Ошибка: введите число.")


def create_delivery_dialog():
    print("Тип: 1 — курьер, 2 — экспресс-курьер, 3 — почта")
    kind = input("Тип: ").strip()
    classes = {"1": CourierDelivery, "2": ExpressCourierDelivery, "3": PostDelivery}
    if kind not in classes:
        raise ValueError("Неизвестный тип доставки")
    sender = Address(input("Город отправителя: "), input("Улица отправителя: "))
    recipient = Address(input("Город получателя: "), input("Улица получателя: "))
    parcel = Parcel(input("Описание посылки: "), read_number("Вес, кг: "))
    distance = read_number("Расстояние, км: ")
    return classes[kind](sender, recipient, parcel, distance)


def main():
    service = create_demo_service()
    run_tests(service)

    while True:
        print("\n===== МЕНЮ: СИСТЕМА ДОСТАВКИ =====")
        print("1. Создать доставку")
        print("2. Показать все доставки")
        print("3. Отправить / завершить / отменить доставку")
        print("4. Изменить расстояние доставки")
        print("5. Удалить доставку")
        print("6. Поиск по городу, статусу и стоимости")
        print("7. Сортировка по стоимости")
        print("8. Статистика")
        print("0. Выход")
        choice = input("Выберите действие: ").strip()
        try:
            if choice == "1":
                delivery = create_delivery_dialog()
                service.add(delivery)
                print("Создана:", delivery)
            elif choice == "2":
                for d in service.all():
                    print(" ", d)
            elif choice == "3":
                delivery = service.find(read_number("Номер: ", int))
                action = input("1 — отправить, 2 — завершить, 3 — отменить: ").strip()
                {"1": delivery.start, "2": delivery.complete, "3": delivery.cancel}[action]()
                print("Готово:", delivery)
            elif choice == "4":
                delivery = service.find(read_number("Номер: ", int))
                delivery.distance = read_number("Новое расстояние, км: ")
                print("Изменено:", delivery)
            elif choice == "5":
                print("Удалена:", service.remove(read_number("Номер: ", int)))
            elif choice == "6":
                city = input("Город получателя (Enter — любой): ").strip() or None
                status = input(f"Статус {Delivery.STATUSES} (Enter — любой): ").strip() or None
                text = input("Максимальная стоимость (Enter — любая): ").strip()
                max_cost = float(text) if text else None
                found = service.search(city, status, max_cost)
                print("\n".join(f"  {d}" for d in found) or "  Ничего не найдено.")
            elif choice == "7":
                for d in service.sorted_by_cost():
                    print(f"  {d.calculate_cost():>10.2f}  {d}")
            elif choice == "8":
                for name, (count, total) in service.statistics().items():
                    print(f"  {name:<16} кол-во: {count}, сумма: {total:.2f} руб.")
                print(f"  Выручка (без отменённых): {service.total_revenue():.2f} руб.")
            elif choice == "0":
                break
            else:
                print("Неизвестный пункт меню.")
        except (ValueError, LookupError, TypeError) as error:
            print("Ошибка:", error)


if __name__ == "__main__":
    main()
