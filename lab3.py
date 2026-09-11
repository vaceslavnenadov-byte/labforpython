# Лабораторная работа №3. Вариант 10. Система доставки
# Объектно-ориентированное программирование в Python

from abc import ABC, abstractmethod


# ============================================================
# Композиция: получатель входит в состав объекта доставки
# ============================================================
class Recipient:
    """Получатель доставки (композиция внутри Delivery)."""

    def __init__(self, name, address):
        self.name = name
        self.address = address

    def __str__(self):
        return f"{self.name} ({self.address})"


# ============================================================
# Базовый абстрактный класс
# ============================================================
class Delivery(ABC):
    """Базовый класс доставки. Определяет общий интерфейс."""

    def __init__(self, number, weight, distance, recipient):
        self._number = number
        self._recipient = recipient          # композиция
        self.weight = weight                 # через property
        self.distance = distance             # через property

    # ---------- Свойства (инкапсуляция) ----------
    @property
    def number(self):
        return self._number

    @property
    def recipient(self):
        return self._recipient

    @property
    def weight(self):
        return self._weight

    @weight.setter
    def weight(self, value):
        if value <= 0:
            raise ValueError("Вес должен быть положительным")
        self._weight = value

    @property
    def distance(self):
        return self._distance

    @distance.setter
    def distance(self, value):
        if value < 0:
            raise ValueError("Расстояние не может быть отрицательным")
        self._distance = value

    # ---------- Абстрактный метод ----------
    @abstractmethod
    def calculate_cost(self):
        """Расчёт стоимости доставки. Реализуется в наследниках."""
        pass

    # ---------- Общий (полиморфный) метод ----------
    def get_info(self):
        return (f"[{self.type_name()}] №{self.number}: "
                f"{self.weight:.2f} кг, {self.distance:.1f} км, "
                f"получатель: {self.recipient}, "
                f"стоимость: {self.calculate_cost():.2f} руб.")

    def type_name(self):
        return self.__class__.__name__

    # ---------- Специальные методы ----------
    def __str__(self):
        return self.get_info()

    def __lt__(self, other):
        return self.calculate_cost() < other.calculate_cost()

    def __eq__(self, other):
        return isinstance(other, Delivery) and self.number == other.number


# ============================================================
# Производный класс 1: курьерская доставка
# ============================================================
class CourierDelivery(Delivery):
    """Курьерская доставка."""

    def __init__(self, number, weight, distance, recipient,
                 courier_name, urgent=False):
        super().__init__(number, weight, distance, recipient)
        self.courier_name = courier_name
        self.urgent = urgent

    def calculate_cost(self):
        cost = 200 + 30 * self.weight + 15 * self.distance
        if self.urgent:
            cost *= 1.5
        return round(cost, 2)

    def get_info(self):
        urgency = " (срочно)" if self.urgent else ""
        return super().get_info() + f" Курьер: {self.courier_name}{urgency}"


# ============================================================
# Производный класс 2: почтовая доставка
# ============================================================
class PostDelivery(Delivery):
    """Почтовая доставка."""

    def __init__(self, number, weight, distance, recipient,
                 department_index, express=False):
        super().__init__(number, weight, distance, recipient)
        self.department_index = department_index
        self.express = express

    def calculate_cost(self):
        cost = 100 + 20 * self.weight + 5 * self.distance
        if self.express:
            cost *= 1.3
        return round(cost, 2)

    def get_info(self):
        express = " (экспресс)" if self.express else ""
        return (super().get_info()
                + f" Отделение: {self.department_index}{express}")


# ============================================================
# Композиция: сервис содержит коллекцию доставок
# ============================================================
class DeliveryService:
    """Сервис доставки, содержит список объектов Delivery."""

    def __init__(self, name):
        self.name = name
        self._deliveries = []

    @property
    def deliveries(self):
        return list(self._deliveries)

    def __len__(self):
        return len(self._deliveries)

    # ---------- Добавление / удаление ----------
    def add(self, delivery):
        self._deliveries.append(delivery)

    def remove_by_number(self, number):
        for i, d in enumerate(self._deliveries):
            if d.number == number:
                return self._deliveries.pop(i)
        return None

    # ---------- Поиск и фильтрация ----------
    def find_by_recipient(self, name):
        name_lower = name.lower()
        return [d for d in self._deliveries
                if name_lower in d.recipient.name.lower()]

    def filter_by_cost(self, minimum):
        return [d for d in self._deliveries
                if d.calculate_cost() >= minimum]

    # ---------- Сортировка ----------
    def sort_by_cost(self, reverse=False):
        return sorted(self._deliveries,
                      key=lambda d: d.calculate_cost(),
                      reverse=reverse)

    # ---------- Статистика ----------
    def total_cost(self):
        total = 0
        for d in self._deliveries:
            total += d.calculate_cost()
        return round(total, 2)

    def average_cost(self):
        if not self._deliveries:
            return 0
        return round(self.total_cost() / len(self._deliveries), 2)

    def most_expensive(self):
        if not self._deliveries:
            return None
        result = self._deliveries[0]
        for d in self._deliveries:
            if d.calculate_cost() > result.calculate_cost():
                result = d
        return result

    # ---------- Полиморфный обход коллекции ----------
    def show_all(self, items=None):
        if items is None:
            items = self._deliveries
        if not items:
            print("Список доставок пуст.")
            return
        for d in items:
            print(d.get_info())


# ============================================================
# Демонстрационные данные
# ============================================================
def load_demo(service: DeliveryService):
    service.add(CourierDelivery(
        "C-001", 2.5, 15, Recipient("Иван Петров", "ул. Ленина, 10"),
        "Алексей", urgent=False))
    service.add(CourierDelivery(
        "C-002", 0.8, 8, Recipient("Анна Сидорова", "пр. Мира, 25"),
        "Дмитрий", urgent=True))
    service.add(PostDelivery(
        "P-101", 5.0, 120, Recipient("Сергей Иванов", "г. Казань"),
        department_index=42, express=False))
    service.add(PostDelivery(
        "P-102", 1.2, 60, Recipient("Мария Кузнецова", "г. Самара"),
        department_index=17, express=True))
    service.add(CourierDelivery(
        "C-003", 10.0, 30, Recipient("ООО Ромашка",
                                     "ул. Промышленная, 5"),
        "Николай", urgent=False))
    print(f"Загружено {len(service)} демонстрационных доставок.")


# ============================================================
# Ручное создание доставки
# ============================================================
def create_delivery_interactive(service: DeliveryService):
    print("\nТип доставки:")
    print("1. Курьерская (CourierDelivery)")
    print("2. Почтовая  (PostDelivery)")
    kind = input("Выбор: ").strip()

    number = input("Номер: ").strip()
    if not number:
        print("Ошибка: номер не может быть пустым.")
        return

    try:
        weight = float(input("Вес (кг): "))
        distance = float(input("Расстояние (км): "))
    except ValueError:
        print("Ошибка: введите числа.")
        return

    r_name = input("ФИО получателя: ").strip()
    r_addr = input("Адрес получателя: ").strip()
    recipient = Recipient(r_name, r_addr)

    try:
        if kind == "1":
            courier = input("Имя курьера: ").strip()
            urgent = input("Срочно? (y/n): ").strip().lower() == "y"
            delivery = CourierDelivery(number, weight, distance,
                                       recipient, courier, urgent)
        elif kind == "2":
            try:
                dep = int(input("Индекс отделения: "))
            except ValueError:
                print("Ошибка: индекс должен быть числом.")
                return
            express = input("Экспресс? (y/n): ").strip().lower() == "y"
            delivery = PostDelivery(number, weight, distance,
                                    recipient, dep, express)
        else:
            print("Неизвестный тип.")
            return
    except ValueError as e:
        print(f"Ошибка: {e}")
        return

    service.add(delivery)
    print(f"Доставка №{number} добавлена.")


# ============================================================
# Тесты (пункт 12 требований)
# ============================================================
def run_tests():
    print("\n===== ТЕСТЫ =====")

    print("\nТест 1. Создание объектов разных типов:")
    c = CourierDelivery("T-1", 2.0, 10,
                        Recipient("Тест1", "Адрес1"), "Курьер1")
    p = PostDelivery("T-2", 3.0, 50,
                     Recipient("Тест2", "Адрес2"), 5)
    print(f"  Создано: {c.type_name()} и {p.type_name()}")

    print("\nТест 2. Общие методы get_info():")
    print(" ", c.get_info())
    print(" ", p.get_info())

    print("\nТест 3. Переопределение calculate_cost():")
    print(f"  Курьер: {c.calculate_cost()} руб.")
    print(f"  Почта:  {p.calculate_cost()} руб.")

    print("\nТест 4. Изменение веса через property:")
    old = c.weight
    c.weight = 5.0
    print(f"  Вес курьерской доставки: {old} -> {c.weight}")

    print("\nТест 5. Негативное значение веса:")
    try:
        c.weight = -1
        print("  ОШИБКА: исключение не сгенерировано!")
    except ValueError as e:
        print(f"  Исключение получено: {e}")

    print("\nТест 6. Полиморфная коллекция:")
    items = [c, p, CourierDelivery("T-3", 1.0, 5,
                                   Recipient("Тест3", "Адрес3"), "Курьер3")]
    for it in items:
        print(f"  {it.type_name()}: {it.calculate_cost()} руб.")

    print("\nТест 7. Композиция (Delivery содержит Recipient):")
    print(f"  {c.number} -> {c.recipient}")

    print("\nДоп. тест. Сравнение объектов (__lt__):")
    if c < p:
        print(f"  Курьерская ({c.calculate_cost()}) дешевле "
              f"почтовой ({p.calculate_cost()})")
    else:
        print(f"  Курьерская ({c.calculate_cost()}) дороже "
              f"почтовой ({p.calculate_cost()})")


# ============================================================
# Главное меню
# ============================================================
def main():
    service = DeliveryService("ГрузЭкспресс")

    while True:
        print("\n===== МЕНЮ СИСТЕМЫ ДОСТАВКИ =====")
        print("1. Добавить доставку")
        print("2. Показать все доставки")
        print("3. Поиск по получателю")
        print("4. Фильтр по стоимости (мин. сумма)")
        print("5. Сортировка по стоимости")
        print("6. Статистика")
        print("7. Удалить доставку по номеру")
        print("8. Загрузить демо-данные")
        print("9. Запустить тесты")
        print("0. Выход")
        choice = input("Выберите действие: ").strip()

        if choice == "1":
            create_delivery_interactive(service)

        elif choice == "2":
            print("\n--- Все доставки ---")
            service.show_all()

        elif choice == "3":
            name = input("Введите часть ФИО получателя: ").strip()
            found = service.find_by_recipient(name)
            print(f"\nНайдено: {len(found)}")
            service.show_all(found)

        elif choice == "4":
            try:
                minimum = float(input("Минимальная стоимость: "))
            except ValueError:
                print("Ошибка: введите число.")
                continue
            found = service.filter_by_cost(minimum)
            print(f"\nНайдено: {len(found)}")
            service.show_all(found)

        elif choice == "5":
            order = input("По возрастанию? (y/n): ").strip().lower()
            reverse = (order == "n")
            sorted_items = service.sort_by_cost(reverse=reverse)
            print("\n--- Отсортировано по стоимости ---")
            service.show_all(sorted_items)

        elif choice == "6":
            if len(service) == 0:
                print("Нет данных.")
                continue
            print("\n=== Статистика ===")
            print(f"Всего доставок: {len(service)}")
            print(f"Суммарная стоимость: {service.total_cost():.2f} руб.")
            print(f"Средняя стоимость: {service.average_cost():.2f} руб.")
            most = service.most_expensive()
            print(f"Самая дорогая доставка: №{most.number} "
                  f"({most.calculate_cost():.2f} руб.)")

        elif choice == "7":
            number = input("Номер доставки для удаления: ").strip()
            removed = service.remove_by_number(number)
            if removed is None:
                print("Доставка с таким номером не найдена.")
            else:
                print(f"Доставка №{number} удалена.")

        elif choice == "8":
            load_demo(service)

        elif choice == "9":
            run_tests()

        elif choice == "0":
            print("Выход из программы.")
            break

        else:
            print("Ошибка: выберите пункт из меню.")


if __name__ == "__main__":
    main()