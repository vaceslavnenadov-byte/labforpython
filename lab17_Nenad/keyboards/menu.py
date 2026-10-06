from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

SCHEDULE = "🚆 Расписание"
SEARCH = "🔎 Найти поезд"
BUY = "🎫 Купить билет"
MY_TICKETS = "📋 Мои билеты"
HELP = "ℹ️ Помощь"
CANCEL = "❌ Отмена"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=SCHEDULE), KeyboardButton(text=SEARCH)],
        [KeyboardButton(text=BUY), KeyboardButton(text=MY_TICKETS)],
        [KeyboardButton(text=HELP)],
    ], resize_keyboard=True)


def cities_keyboard(cities: list[str]) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=c) for c in cities[i:i + 3]] for i in range(0, len(cities), 3)]
    rows.append([KeyboardButton(text=CANCEL)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=CANCEL)]], resize_keyboard=True)
