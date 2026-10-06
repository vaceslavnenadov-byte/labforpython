"""Обработчики «последней линии»: неизвестные сообщения и ошибки."""

import logging

from aiogram import Router
from aiogram.types import ErrorEvent, Message

from keyboards import menu

router = Router(name="common")
logger = logging.getLogger("bot")


@router.message()
async def unknown(message: Message) -> None:
    await message.answer("Не понял команду 🤔 Воспользуйтесь меню или /help.", reply_markup=menu.main_menu())


@router.errors()
async def on_error(event: ErrorEvent) -> bool:
    logger.exception("Ошибка при обработке обновления", exc_info=event.exception)
    target = event.update.message or (event.update.callback_query and event.update.callback_query.message)
    if target:
        await target.answer("Произошла ошибка. Попробуйте ещё раз или /cancel.")
    return True
