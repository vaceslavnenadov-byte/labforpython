import random

# Названия месяцев
MONTHS = [
    "Январь", "Февраль", "Март", "Апрель",
    "Май", "Июнь", "Июль", "Август",
    "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]


def input_incomes():
    """Ручной ввод доходов за 12 месяцев."""
    incomes = []
    print("\nВведите доход за каждый месяц (неотрицательное число):")
    for month in MONTHS:
        while True:
            try:
                value = float(input(f"{month}: "))
                if value < 0:
                    print("Ошибка: доход не может быть отрицательным.")
                    continue
                incomes.append(value)
                break
            except ValueError:
                print("Ошибка: введите число.")
    return incomes


def generate_incomes():
    """Генерация случайных доходов за 12 месяцев."""
    return [round(random.uniform(0, 1_000_000), 2) for _ in range(12)]


def calculate_total(incomes):
    """Годовой доход."""
    return sum(incomes)


def calculate_average(incomes):
    """Среднемесячный доход."""
    if not incomes:
        return 0
    return sum(incomes) / len(incomes)


def find_max_month(incomes):
    """Наиболее прибыльный месяц: возвращает индекс и значение."""
    max_value = max(incomes)
    max_index = incomes.index(max_value)
    return max_index, max_value


def find_min_month(incomes):
    """Наименее прибыльный месяц: возвращает индекс и значение."""
    min_value = min(incomes)
    min_index = incomes.index(min_value)
    return min_index, min_value


def count_above_average(incomes):
    """Количество месяцев с доходом выше среднего."""
    avg = calculate_average(incomes)
    return sum(1 for value in incomes if value > avg)


def print_statistics(incomes):
    """Вывод основной статистики."""
    if not incomes:
        print("\nДанные не введены. Сначала введите или сгенерируйте доходы.")
        return

    total = calculate_total(incomes)
    avg = calculate_average(incomes)
    max_index, max_value = find_max_month(incomes)
    min_index, min_value = find_min_month(incomes)
    above_avg = count_above_average(incomes)

    print("\n=== Результаты анализа доходов предприятия ===")
    print(f"Годовой доход: {total:.2f}")
    print(f"Среднемесячный доход: {avg:.2f}")
    print(f"Наиболее прибыльный месяц: {MONTHS[max_index]} ({max_value:.2f})")
    print(f"Наименее прибыльный месяц: {MONTHS[min_index]} ({min_value:.2f})")
    print(f"Количество месяцев с доходом выше среднего: {above_avg}")


def additional_analysis(incomes):
    """Дополнительный анализ для повышенной оценки."""
    if not incomes:
        print("\nДанные не введены. Сначала введите или сгенерируйте доходы.")
        return

    avg = calculate_average(incomes)
    sorted_incomes = sorted(incomes)
    median = (sorted_incomes[5] + sorted_incomes[6]) / 2
    below_avg = sum(1 for value in incomes if value < avg)
    difference = max(incomes) - min(incomes)

    above_months = [
        MONTHS[i] for i, value in enumerate(incomes) if value > avg
    ]

    print("\n=== Дополнительный анализ ===")
    print(f"Медианный доход: {median:.2f}")
    print(f"Количество месяцев с доходом ниже среднего: {below_avg}")
    print(f"Разница между максимальным и минимальным доходом: {difference:.2f}")
    if above_months:
        print("Месяцы с доходом выше среднего:", ", ".join(above_months))
    else:
        print("Месяцев с доходом выше среднего нет.")


def main():
    """Главная функция с меню приложения."""
    incomes = []

    while True:
        print("\n===== Анализ доходов предприятия =====")
        print("1. Ввести данные вручную")
        print("2. Сгенерировать случайные данные")
        print("3. Показать статистику")
        print("4. Выполнить дополнительный анализ")
        print("5. Выход")
        choice = input("Выберите действие: ").strip()

        if choice == "1":
            incomes = input_incomes()
            print("Данные успешно сохранены.")
        elif choice == "2":
            incomes = generate_incomes()
            print("\nСгенерированы случайные данные:")
            for month, value in zip(MONTHS, incomes):
                print(f"{month}: {value:.2f}")
        elif choice == "3":
            print_statistics(incomes)
        elif choice == "4":
            additional_analysis(incomes)
        elif choice == "5":
            print("Выход из программы.")
            break
        else:
            print("Ошибка: выберите пункт от 1 до 5.")


if __name__ == "__main__":
    main()