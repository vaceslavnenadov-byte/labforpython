"""
Лабораторная работа №2. Коллекции, строки и функции в Python.
Вариант 10. Рейсы.

Для каждого рейса хранятся: номер, направление, продолжительность (ч),
количество пассажиров. Данные хранятся в списке словарей.

Реализовано:
- поиск рейсов по направлению;
- фильтрация по количеству пассажиров;
- среднее количество пассажиров;
- поиск самого продолжительного рейса;
- множество уникальных направлений;
- сортировка по продолжительности.
Дополнительно: удаление и изменение рейса, фильтр по нескольким критериям,
сортировка по двум параметрам, группировка по направлению.
"""

DEMO_FLIGHTS = [
    ("SU1402", "Москва - Сочи", 2.5, 180),
    ("S7-201", "Новосибирск - Москва", 4.2, 150),
    ("DP-405", "Москва - Калининград", 2.1, 189),
    ("SU1124", "Москва - Сочи", 2.4, 165),
    ("U6-263", "Екатеринбург - Москва", 2.3, 120),
    ("FV6512", "Санкт-Петербург - Сочи", 3.6, 0),
    ("SU0100", "Москва - Владивосток", 8.9, 310),
]


# ---------- Создание и ввод ----------

def make_flight(number, direction, duration, passengers):
    """Создаёт словарь рейса."""
    return {
        "number": number.strip().upper(),
        "direction": normalize_direction(direction),
        "duration": float(duration),
        "passengers": int(passengers),
    }


def normalize_direction(direction):
    """Приводит направление к виду 'Москва - Сочи'.

    Разделители: ' - ', '->' или '—' (одиночный дефис оставлен для
    составных названий, например «Санкт-Петербург»).
    """
    for separator in ("->", "—", " - "):
        direction = direction.replace(separator, "|")
    parts = [part.strip().title() for part in direction.split("|") if part.strip()]
    return " - ".join(parts)


def read_float(prompt, minimum=0.0):
    while True:
        try:
            value = float(input(prompt).replace(",", "."))
        except ValueError:
            print("  Ошибка: введите число.")
            continue
        if value <= minimum:
            print(f"  Ошибка: значение должно быть больше {minimum}.")
            continue
        return value


def read_int(prompt, minimum=0):
    while True:
        try:
            value = int(input(prompt))
        except ValueError:
            print("  Ошибка: введите целое число.")
            continue
        if value < minimum:
            print(f"  Ошибка: значение не может быть меньше {minimum}.")
            continue
        return value


def read_text(prompt):
    while True:
        text = input(prompt).strip()
        if text:
            return text
        print("  Ошибка: строка не может быть пустой.")


def input_flight(flights):
    """Ввод одного рейса с проверкой уникальности номера."""
    while True:
        number = read_text("Номер рейса: ").upper()
        if find_by_number(flights, number) is None:
            break
        print("  Ошибка: рейс с таким номером уже существует.")
    direction = read_text("Направление (Откуда -> Куда): ")
    duration = read_float("Продолжительность, ч: ")
    passengers = read_int("Количество пассажиров: ")
    return make_flight(number, direction, duration, passengers)


# ---------- Поиск, фильтрация, сортировка ----------

def find_by_number(flights, number):
    for flight in flights:
        if flight["number"] == number.upper():
            return flight
    return None


def find_by_direction(flights, text):
    """Поиск по части направления без учёта регистра."""
    text = text.lower()
    return [flight for flight in flights if text in flight["direction"].lower()]


def filter_by_passengers(flights, minimum, maximum=None):
    result = []
    for flight in flights:
        if flight["passengers"] < minimum:
            continue
        if maximum is not None and flight["passengers"] > maximum:
            continue
        result.append(flight)
    return result


def filter_multi(flights, min_passengers, max_duration):
    """Фильтр по нескольким критериям."""
    return [
        flight for flight in flights
        if flight["passengers"] >= min_passengers and flight["duration"] <= max_duration
    ]


def sort_by_duration(flights, reverse=False):
    return sorted(flights, key=lambda flight: flight["duration"], reverse=reverse)


def sort_by_direction_and_passengers(flights):
    """Сортировка по двум параметрам: направление, затем пассажиры по убыванию."""
    return sorted(flights, key=lambda f: (f["direction"], -f["passengers"]))


# ---------- Статистика ----------

def average_passengers(flights):
    if not flights:
        return 0
    return sum(flight["passengers"] for flight in flights) / len(flights)


def longest_flight(flights):
    if not flights:
        return None
    return max(flights, key=lambda flight: flight["duration"])


def total_passengers(flights):
    total = 0
    for flight in flights:
        total += flight["passengers"]
    return total


def unique_directions(flights):
    return {flight["direction"] for flight in flights}


def unique_cities(flights):
    """Множество всех городов, участвующих в рейсах."""
    cities = set()
    for flight in flights:
        cities.update(flight["direction"].split(" - "))
    return cities


def group_by_direction(flights):
    groups = {}
    for flight in flights:
        groups.setdefault(flight["direction"], []).append(flight)
    return groups


# ---------- Изменение ----------

def delete_flight(flights, number):
    flight = find_by_number(flights, number)
    if flight is None:
        return False
    flights.remove(flight)
    return True


def update_passengers(flights, number, passengers):
    flight = find_by_number(flights, number)
    if flight is None:
        return False
    flight["passengers"] = passengers
    return True


# ---------- Вывод ----------

def print_flights(flights, title="Рейсы"):
    print(f"\n{title}:")
    if not flights:
        print("  Нет подходящих рейсов.")
        return
    print(f"  {'№':<3}{'Рейс':<9}{'Направление':<28}{'Время, ч':>9}{'Пассажиры':>11}")
    for index, flight in enumerate(flights, start=1):
        print(f"  {index:<3}{flight['number']:<9}{flight['direction']:<28}"
              f"{flight['duration']:>9.1f}{flight['passengers']:>11}")


def print_statistics(flights):
    if not flights:
        print("Нет данных для статистики.")
        return
    longest = longest_flight(flights)
    print("\n===== Статистика =====")
    print(f"Количество рейсов:            {len(flights)}")
    print(f"Всего пассажиров:             {total_passengers(flights)}")
    print(f"Среднее число пассажиров:     {average_passengers(flights):.1f}")
    print(f"Самый продолжительный рейс:   {longest['number']} ({longest['direction']}, {longest['duration']} ч)")
    print(f"Суммарное время в полёте:     {sum(f['duration'] for f in flights):.1f} ч")
    empty = [f["number"] for f in flights if f["passengers"] == 0]
    print(f"Рейсы без пассажиров:         {', '.join(empty) if empty else 'нет'}")


def main():
    flights = [make_flight(*data) for data in DEMO_FLIGHTS]
    actions = {
        "1": "Добавить рейс",
        "2": "Показать все рейсы",
        "3": "Найти рейсы по направлению",
        "4": "Фильтрация по количеству пассажиров",
        "5": "Сортировка по продолжительности",
        "6": "Статистика",
        "7": "Уникальные направления и города",
        "8": "Фильтр: пассажиры + длительность",
        "9": "Сортировка: направление + пассажиры",
        "10": "Группировка по направлению",
        "11": "Изменить число пассажиров",
        "12": "Удалить рейс",
        "0": "Выход",
    }
    while True:
        print("\n===== МЕНЮ: РЕЙСЫ =====")
        for key, title in actions.items():
            print(f"{key}. {title}")
        choice = input("Выберите действие: ").strip()

        if choice == "1":
            count = read_int("Сколько рейсов добавить? ", minimum=1)
            for _ in range(count):
                flights.append(input_flight(flights))
            print("Рейсы добавлены.")
        elif choice == "2":
            print_flights(flights, "Все рейсы")
        elif choice == "3":
            text = read_text("Город или направление: ")
            print_flights(find_by_direction(flights, text), f"Рейсы по запросу «{text}»")
        elif choice == "4":
            minimum = read_int("Минимум пассажиров: ")
            print_flights(filter_by_passengers(flights, minimum), f"Рейсы с пассажирами >= {minimum}")
        elif choice == "5":
            order = input("По убыванию? (д/н): ").strip().lower()
            print_flights(sort_by_duration(flights, reverse=order == "д"), "Рейсы по продолжительности")
        elif choice == "6":
            print_statistics(flights)
        elif choice == "7":
            print("Уникальные направления:", ", ".join(sorted(unique_directions(flights))))
            print("Уникальные города:", ", ".join(sorted(unique_cities(flights))))
        elif choice == "8":
            minimum = read_int("Минимум пассажиров: ")
            max_duration = read_float("Максимальная длительность, ч: ")
            print_flights(filter_multi(flights, minimum, max_duration), "Результат фильтрации")
        elif choice == "9":
            print_flights(sort_by_direction_and_passengers(flights), "Сортировка по двум параметрам")
        elif choice == "10":
            for direction, group in group_by_direction(flights).items():
                numbers = ", ".join(f["number"] for f in group)
                print(f"  {direction}: {numbers} (пассажиров: {total_passengers(group)})")
        elif choice == "11":
            number = read_text("Номер рейса: ")
            passengers = read_int("Новое количество пассажиров: ")
            print("Изменено." if update_passengers(flights, number, passengers) else "Рейс не найден.")
        elif choice == "12":
            number = read_text("Номер рейса: ")
            print("Удалено." if delete_flight(flights, number) else "Рейс не найден.")
        elif choice == "0":
            print("Работа завершена.")
            break
        else:
            print("Неизвестный пункт меню.")


if __name__ == "__main__":
    main()
