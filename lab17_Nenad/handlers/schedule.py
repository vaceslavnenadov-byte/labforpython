from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from handlers.formatting import train_text
from keyboards import menu
from keyboards.inline import TrainCallback, train_info_keyboard, trains_keyboard
from services.railway_service import BookingError, RailwayService

router = Router(name="schedule")


@router.message(Command("schedule"))
@router.message(F.text == menu.SCHEDULE)
async def show_schedule(message: Message, service: RailwayService) -> None:
    trains = await service.schedule()
    if not trains:
        await message.answer("Ближайших отправлений нет.")
        return
    await message.answer("Ближайшие отправления. Нажмите на поезд, чтобы узнать подробности:",
                         reply_markup=trains_keyboard(trains, action="info"))


@router.callback_query(TrainCallback.filter(F.action == "info"))
async def train_info(callback: CallbackQuery, callback_data: TrainCallback, service: RailwayService) -> None:
    try:
        train = await service.get_train(callback_data.train_id)
    except BookingError as error:
        await callback.answer(str(error), show_alert=True)   # например, нажата устаревшая кнопка
        return
    await callback.message.answer(train_text(train), reply_markup=train_info_keyboard(train.id))
    await callback.answer()
