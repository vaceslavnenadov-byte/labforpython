"""Просмотр, изменение и удаление (возврат) своих билетов."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.models import User
from handlers.formatting import ticket_text
from keyboards import menu
from keyboards.inline import TicketCallback, ticket_actions_keyboard, tickets_keyboard
from services.railway_service import BookingError, RailwayService
from services.validation import InputError, validate_passenger_name
from states.booking import RenameStates

router = Router(name="tickets")


@router.message(Command("mytickets"))
@router.message(F.text == menu.MY_TICKETS)
async def my_tickets(message: Message, service: RailwayService, user: User) -> None:
    tickets = await service.user_tickets(user)
    if not tickets:
        await message.answer("У вас пока нет билетов. Купить: /buy")
        return
    await message.answer(f"Ваши билеты ({len(tickets)}):", reply_markup=tickets_keyboard(tickets))


@router.callback_query(TicketCallback.filter(F.action == "show"))
async def show_ticket(callback: CallbackQuery, callback_data: TicketCallback, service: RailwayService, user: User) -> None:
    try:
        ticket = await service.get_own_ticket(user, callback_data.ticket_id)
    except BookingError as error:
        await callback.answer(str(error), show_alert=True)
        return
    await callback.message.answer(ticket_text(ticket), reply_markup=ticket_actions_keyboard(ticket))
    await callback.answer()


@router.callback_query(TicketCallback.filter(F.action == "return"))
async def return_ticket(callback: CallbackQuery, callback_data: TicketCallback, service: RailwayService, user: User) -> None:
    try:
        refund = await service.return_ticket(user, callback_data.ticket_id)
    except BookingError as error:
        await callback.answer(str(error), show_alert=True)
        return
    await callback.message.answer(f"↩️ Билет №{callback_data.ticket_id} возвращён. К возврату {refund:.2f} ₽ (90%).")
    await callback.answer()


@router.callback_query(TicketCallback.filter(F.action == "rename"))
async def rename_start(callback: CallbackQuery, callback_data: TicketCallback, state: FSMContext) -> None:
    await state.set_state(RenameStates.new_name)
    await state.update_data(ticket_id=callback_data.ticket_id)
    await callback.message.answer("Введите новое ФИО пассажира (или /cancel):", reply_markup=menu.cancel_keyboard())
    await callback.answer()


@router.message(RenameStates.new_name, F.text)
async def rename_finish(message: Message, state: FSMContext, service: RailwayService, user: User) -> None:
    try:
        name = validate_passenger_name(message.text)
        ticket = await service.rename_passenger(user, (await state.get_data())["ticket_id"], name)
    except (InputError, BookingError) as error:
        await message.answer(f"⚠️ {error}")
        return
    await state.clear()
    await message.answer("✏️ Изменено.\n\n" + ticket_text(ticket), reply_markup=menu.main_menu())
