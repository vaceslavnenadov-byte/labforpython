# Лабораторная работа №2. Вариант 10. Рейсы
# Коллекции, строки и функции в Python

flights = []  # список словарей


def input_flight():
    """Ввод одного рейса с проверкой корректности."""
    number = input("Номер рейса: ").strip()
    if not number:
        print("Ошибка: номер рейса не может быть пустым.")
        return None

    direction = input("Направление: ").strip()
    if not direction:
        print("Ошибка: направление не может быть пустым.")
        return None

    try:
        duration = float(input("Продолжительность (часы): "))
        if duration <= 0:
            print("Ошибка: продолжительность должна быть положительной.")
            return None
    except ValueError:
        print("Ошибка: продолжительность должна быть числом.")
        return None

    try:
        passengers = int(input("Количество пассажиров: "))
        if passengers < 0:
            print("Ошибка: количество пассажиров не может быть отрицательным.")
            return None
    except ValueError:
        print("Ошибка: количество пассажиров должно быть целым числом.")
        return None

    return {
        "number": number,
        "direction": direction,
        "duration": duration,
        "passengers": passengers,
    }


def add_flight():
    """Добавление рейса (или нескольких)."""
    while True:
        flight = input_flight()
        if flight is not None:
            flights.append(flight)
            print(f"Рейс {flight['number']} добавлен.")
        else:
            print("Рейс не добавлен.")

        answer = input("Добавить ещё один рейс? (y/n): ").strip().lower()
        if answer != "y":
            break


def show_flights(items=None):
    """Вывод списка рейсов в виде таблицы."""
    if items is None:
        items = flights
    if not items:
        print("\nСписок рейсов пуст.")
        return

    print("\n{:<12}{:<20}{:<15}{:<12}".format(
        "Номер", "Направление", "Длит. (ч)", "Пассажиры"))
    print("-" * 60)
    for f in items:
        print("{:<12}{:<20}{:<15}{:<12}".format(
            f["number"], f["direction"], f["duration"], f["passengers"]))


def find_by_direction(direction):
    """Поиск рейсов по направлению."""
    return [f for f in flights if f["direction"].lower() == direction.lower()]


def search_flights():
    """Меню поиска."""
    if not flights:
        print("\nСписок рейсов пуст.")
        return
    direction = input("Введите направление для поиска: ").strip()
    found = find_by_direction(direction)
    if found:
        print(f"\nНайдено рейсов: {len(found)}")
        show_flights(found)
    else:
        print(f"\nРейсы по направлению «{direction}» не найдены.")


def filter_by_passengers():
    """Фильтрация рейсов по количеству пассажиров."""
    if not flights:
        print("\nСписок рейсов пуст.")
        return
    try:
        minimum = int(input("Минимальное количество пассажиров: "))
        if minimum < 0:
            print("Ошибка: значение не может быть отрицательным.")
            return
    except ValueError:
        print("Ошибка: введите целое число.")
        return

    filtered = [f for f in flights if f["passengers"] >= minimum]
    if filtered:
        print(f"\nНайдено рейсов: {len(filtered)}")
        show_flights(filtered)
    else:
        print("\nНет рейсов, удовлетворяющих условию.")


def calculate_average_passengers(items=None):
    """Среднее количество пассажиров."""
    if items is None:
        items = flights
    if not items:
        return 0
    total = 0
    for f in items:
        total += f["passengers"]
    return total / len(items)


def find_longest_flight():
    """Самый продолжительный рейс."""
    if not flights:
        return None
    longest = flights[0]
    for f in flights:
        if f["duration"] > longest["duration"]:
            longest = f
    return longest


def sort_by_duration():
    """Сортировка рейсов по продолжительности (по возрастанию)."""
    if not flights:
        print("\nСписок рейсов пуст.")
        return
    order = input("По возрастанию? (y/n): ").strip().lower()
    reverse = (order == "n")
    sorted_flights = sorted(flights, key=lambda f: f["duration"],
                            reverse=reverse)
    print("\nОтсортированный список рейсов:")
    show_flights(sorted_flights)


def get_unique_directions():
    """Множество уникальных направлений."""
    return {f["direction"] for f in flights}


def show_statistics():
    """Статистика по рейсам."""
    if not flights:
        print("\nСписок рейсов пуст.")
        return

    total_flights = len(flights)
    avg_passengers = calculate_average_passengers()
    longest = find_longest_flight()

    total_passengers = sum(f["passengers"] for f in flights)
    avg_duration = sum(f["duration"] for f in flights) / total_flights
    max_passengers_flight = max(flights, key=lambda f: f["passengers"])

    print("\n=== Статистика по рейсам ===")
    print(f"Всего рейсов: {total_flights}")
    print(f"Среднее количество пассажиров: {avg_passengers:.2f}")
    print(f"Суммарное количество пассажиров: {total_passengers}")
    print(f"Средняя продолжительность рейса: {avg_duration:.2f} ч")
    print(f"Самый продолжительный рейс: {longest['number']} "
          f"({longest['direction']}, {longest['duration']} ч)")
    print(f"Рейс с максимальным числом пассажиров: "
          f"{max_passengers_flight['number']} "
          f"({max_passengers_flight['passengers']} чел.)")


def show_unique_directions():
    """Вывод уникальных направлений."""
    if not flights:
        print("\nСписок рейсов пуст.")
        return
    unique = get_unique_directions()
    print(f"\nУникальных направлений: {len(unique)}")
    for d in sorted(unique):
        print(f" - {d}")


def load_demo_data():
    """Заполнение демонстрационными данными."""
    global flights
    flights = [
        {"number": "SU-100", "direction": "Москва",
         "duration": 3.5, "passengers": 180},
        {"number": "SU-205", "direction": "Казань",
         "duration": 1.8, "passengers": 95},
        {"number": "SU-310", "direction": "Москва",
         "duration": 3.2, "passengers": 210},
        {"number": "SU-412", "direction": "Самара",
         "duration": 2.4, "passengers": 120},
        {"number": "SU-550", "direction": "Казань",
         "duration": 1.5, "passengers": 80},
        {"number": "SU-601", "direction": "Новосибирск",
         "duration": 4.7, "passengers": 250},
    ]
    print("Загружено 6 демонстрационных рейсов.")


def main():
    """Главное меню приложения."""
    while True:
        print("\n===== МЕНЮ =====")
        print("1. Добавить рейс")
        print("2. Показать все рейсы")
        print("3. Найти рейс по направлению")
        print("4. Фильтр по количеству пассажиров")
        print("5. Сортировка по продолжительности")
        print("6. Статистика")
        print("7. Уникальные направления")
        print("8. Загрузить демо-данные")
        print("0. Выход")

        choice = input("Выберите действие: ").strip()

        if choice == "1":
            add_flight()
        elif choice == "2":
            show_flights()
        elif choice == "3":
            search_flights()
        elif choice == "4":
            filter_by_passengers()
        elif choice == "5":
            sort_by_duration()
        elif choice == "6":
            show_statistics()
        elif choice == "7":
            show_unique_directions()
        elif choice == "8":
            load_demo_data()
        elif choice == "0":
            print("Выход из программы.")
            break
        else:
            print("Ошибка: выберите пункт из меню.")


if __name__ == "__main__":
    main()