"""
ЛР №17. Асинхронный Telegram-бот на aiogram 3.
Вариант 10. Железнодорожные билеты: поезд, станция, пассажир, билет.

Запуск: BOT_TOKEN=... python bot.py   (см. .env.example)
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import config
from database.db import create_engine, create_session_factory, init_models
from database.seed import seed
from handlers import admin, booking, common, schedule, start, tickets
from middlewares.middlewares import LoggingMiddleware, ServiceMiddleware


def build_dispatcher(session_factory, admin_ids: frozenset[int]) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    logging_mw = LoggingMiddleware()
    service_mw = ServiceMiddleware(session_factory, admin_ids)
    for observer in (dp.message, dp.callback_query):
        observer.outer_middleware(logging_mw)
        observer.outer_middleware(service_mw)
    # порядок важен: специфичные роутеры раньше «последней линии» common
    dp.include_routers(start.router, admin.router, schedule.router, booking.router, tickets.router, common.router)
    dp["service_middleware"] = service_mw
    return dp


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not config.bot_token:
        raise SystemExit("Не задан BOT_TOKEN (переменная окружения или файл .env)")
    engine = create_engine(config.database_url)
    await init_models(engine)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        await seed(session)

    bot = Bot(config.bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="schedule", description="Расписание"),
        BotCommand(command="buy", description="Купить билет"),
        BotCommand(command="mytickets", description="Мои билеты"),
        BotCommand(command="cancel", description="Отменить операцию"),
        BotCommand(command="help", description="Справка"),
    ])
    dp = build_dispatcher(session_factory, config.admin_ids)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
