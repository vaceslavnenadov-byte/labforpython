from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database.models import User
from keyboards import menu

router = Router(name="start")

HELP_TEXT = (
    "Я помогу купить железнодорожный билет.\n\n"
    "/start — главное меню\n"
    "/schedule — ближайшие отправления\n"
    "/search — поиск поезда по городам\n"
    "/buy — купить билет\n"
    "/mytickets — мои билеты (просмотр, изменение, возврат)\n"
    "/cancel — отменить текущую операцию\n"
    "/help — эта справка"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, user: User) -> None:
    await state.clear()
    await message.answer(f"Здравствуйте, {user.full_name}! 🚆\nВыберите действие в меню.", reply_markup=menu.main_menu())


@router.message(Command("help"))
@router.message(F.text == menu.HELP)
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=menu.main_menu())


@router.message(Command("cancel"), StateFilter("*"))
@router.message(F.text == menu.CANCEL, StateFilter("*"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer("Нечего отменять.", reply_markup=menu.main_menu())
        return
    await state.clear()
    await message.answer("Операция отменена.", reply_markup=menu.main_menu())
