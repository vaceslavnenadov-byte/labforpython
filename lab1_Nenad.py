"""
Лабораторная работа №1. Основы программирования на Python.
Вариант 10. Доходы предприятия.

Программа анализирует доходы предприятия по месяцам:
- годовой доход;
- среднемесячный доход;
- наиболее и наименее прибыльный месяц;
- количество месяцев с доходом выше среднего.

Дополнительно: меню, несколько наборов данных (годов),
дополнительные показатели (медиана, размах, прирост, кварталы).
"""

import random

MONTHS = (
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
)
MAX_INCOME = 1_000_000_000  # разумная верхняя граница дохода за месяц


# ---------- Ввод данных ----------

def read_income(prompt):
    """Запрашивает доход за месяц, пока не будет введено корректное число."""
    while True:
        text = input(prompt).strip().replace(",", ".").replace(" ", "")
        if text == "":
            print("  Ошибка: значение не может быть пустым.")
            continue
        # Проверка без исключений: допускаются только цифры и одна точка
        if text.count(".") > 1 or not text.replace(".", "").isdigit():
            print("  Ошибка: введите неотрицательное число (например, 125000.50).")
            continue
        value = float(text)
        if value > MAX_INCOME:
            print(f"  Ошибка: доход не может превышать {MAX_INCOME:,}.")
            continue
        return value


def input_incomes():
    """Ручной ввод доходов за 12 месяцев."""
    print("\nВведите доход за каждый месяц (руб.):")
    incomes = []
    for month in MONTHS:
        incomes.append(read_income(f"  {month}: "))
    return incomes


def generate_incomes(minimum=50_000, maximum=500_000):
    """Генерирует случайные доходы за 12 месяцев."""
    return [round(random.uniform(minimum, maximum), 2) for _ in MONTHS]


# ---------- Вычисления ----------

def calculate_total(incomes):
    """Годовой доход (сумма считается циклом)."""
    total = 0
    for income in incomes:
        total += income
    return total


def calculate_average(incomes):
    """Среднемесячный доход."""
    if len(incomes) == 0:
        return 0
    return calculate_total(incomes) / len(incomes)


def find_max_month(incomes):
    """Индекс наиболее прибыльного месяца."""
    best = 0
    for i in range(1, len(incomes)):
        if incomes[i] > incomes[best]:
            best = i
    return best


def find_min_month(incomes):
    """Индекс наименее прибыльного месяца."""
    worst = 0
    for i in range(1, len(incomes)):
        if incomes[i] < incomes[worst]:
            worst = i
    return worst


def count_above_average(incomes):
    """Количество месяцев с доходом выше среднего."""
    average = calculate_average(incomes)
    count = 0
    for income in incomes:
        if income > average:
            count += 1
    return count


def calculate_median(incomes):
    """Медиана доходов."""
    ordered = sorted(incomes)
    n = len(ordered)
    middle = n // 2
    if n % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def calculate_quarters(incomes):
    """Доход по кварталам."""
    quarters = []
    for q in range(4):
        quarters.append(calculate_total(incomes[q * 3:q * 3 + 3]))
    return quarters


def calculate_growth(incomes):
    """Прирост дохода декабря относительно января в процентах."""
    if incomes[0] == 0:
        return None
    return (incomes[-1] - incomes[0]) / incomes[0] * 100


def describe_result(incomes):
    """Текстовая характеристика стабильности доходов."""
    average = calculate_average(incomes)
    if average == 0:
        return "Предприятие не получало доход."
    spread = (max(incomes) - min(incomes)) / average * 100
    if spread < 30:
        return "Доходы стабильны в течение года."
    elif spread < 80:
        return "Доходы умеренно колеблются по месяцам."
    else:
        return "Доходы сильно колеблются, бизнес носит сезонный характер."


# ---------- Вывод ----------

def money(value):
    return f"{value:,.2f} руб.".replace(",", " ")


def print_incomes(incomes):
    print("\nДоходы по месяцам:")
    average = calculate_average(incomes)
    for month, income in zip(MONTHS, incomes):
        mark = "↑" if income > average else " "
        print(f"  {month:<9} {money(income):>22} {mark}")


def print_statistics(incomes):
    max_i = find_max_month(incomes)
    min_i = find_min_month(incomes)
    print("\n===== Основные показатели =====")
    print(f"Годовой доход:              {money(calculate_total(incomes))}")
    print(f"Среднемесячный доход:       {money(calculate_average(incomes))}")
    print(f"Наиболее прибыльный месяц:  {MONTHS[max_i]} ({money(incomes[max_i])})")
    print(f"Наименее прибыльный месяц:  {MONTHS[min_i]} ({money(incomes[min_i])})")
    print(f"Месяцев выше среднего:      {count_above_average(incomes)}")


def print_extra_analysis(incomes):
    print("\n===== Дополнительный анализ =====")
    print(f"Медиана:          {money(calculate_median(incomes))}")
    print(f"Размах:           {money(max(incomes) - min(incomes))}")
    growth = calculate_growth(incomes)
    if growth is None:
        print("Прирост за год:   нельзя вычислить (доход в январе равен 0)")
    else:
        print(f"Прирост за год:   {growth:+.1f}%")
    for number, value in enumerate(calculate_quarters(incomes), start=1):
        print(f"{number}-й квартал:      {money(value)}")
    print(describe_result(incomes))


def compare_years(datasets):
    """Сравнение нескольких наборов данных (лет)."""
    print("\n===== Сравнение наборов данных =====")
    best_name = None
    best_total = -1
    for name, incomes in datasets.items():
        total = calculate_total(incomes)
        print(f"{name:<10} годовой доход: {money(total)}")
        if total > best_total:
            best_total, best_name = total, name
    print(f"Лучший год: {best_name}")


# ---------- Меню ----------

def read_choice(prompt, allowed):
    while True:
        choice = input(prompt).strip()
        if choice in allowed:
            return choice
        print("Ошибка: выберите один из пунктов: " + ", ".join(allowed))


def main():
    datasets = {}   # название набора -> список доходов
    current = None

    while True:
        print("\n===== Анализ доходов предприятия =====")
        print(f"Текущий набор: {current or 'не выбран'}")
        print("1. Ввести данные вручную")
        print("2. Сгенерировать данные случайно")
        print("3. Показать доходы")
        print("4. Показать основные показатели")
        print("5. Дополнительный анализ")
        print("6. Выбрать другой набор данных")
        print("7. Сравнить наборы данных")
        print("0. Выход")
        choice = read_choice("Выберите действие: ", ["1", "2", "3", "4", "5", "6", "7", "0"])

        if choice in ("1", "2"):
            name = input("Название набора (например, 2025): ").strip() or f"Набор {len(datasets) + 1}"
            datasets[name] = input_incomes() if choice == "1" else generate_incomes()
            current = name
            print(f"Набор «{name}» сохранён.")
        elif choice == "0":
            print("Работа завершена.")
            break
        elif choice == "7":
            if len(datasets) < 2:
                print("Для сравнения нужно минимум два набора данных.")
            else:
                compare_years(datasets)
        elif choice == "6":
            if not datasets:
                print("Наборов пока нет.")
                continue
            names = list(datasets)
            for i, name in enumerate(names, start=1):
                print(f"  {i}. {name}")
            index = read_choice("Номер набора: ", [str(i) for i in range(1, len(names) + 1)])
            current = names[int(index) - 1]
        elif current is None:
            print("Сначала введите или сгенерируйте данные.")
        elif choice == "3":
            print_incomes(datasets[current])
        elif choice == "4":
            print_statistics(datasets[current])
        elif choice == "5":
            print_extra_analysis(datasets[current])


if __name__ == "__main__":
    main()
