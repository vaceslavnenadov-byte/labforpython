"""FSM-сценарий покупки: откуда → куда → поезд → тип вагона → место → ФИО → подтверждение."""

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.models import User, WagonType
from handlers.formatting import ticket_text, train_text
from keyboards import menu
from keyboards.inline import ConfirmCallback, TrainCallback, WagonCallback, confirm_keyboard, trains_keyboard, wagons_keyboard
from services.railway_service import BookingError, RailwayService
from services.validation import InputError, validate_city, validate_passenger_name, validate_seat
from states.booking import BookingStates

router = Router(name="booking")


@router.message(Command("buy", "search"))
@router.message(F.text.in_({menu.BUY, menu.SEARCH}))
async def start_booking(message: Message, state: FSMContext, service: RailwayService) -> None:
    await state.clear()
    await state.set_state(BookingStates.from_city)
    await message.answer("Шаг 1/6. Откуда едем? Выберите или введите город.",
                         reply_markup=menu.cities_keyboard(await service.cities()))


@router.message(BookingStates.from_city, F.text)
async def got_from_city(message: Message, state: FSMContext, service: RailwayService) -> None:
    try:
        city = validate_city(message.text)
    except InputError as error:
        await message.answer(f"⚠️ {error}")
        return
    await state.update_data(from_city=city)
    await state.set_state(BookingStates.to_city)
    cities = [c for c in await service.cities() if c != city]
    await message.answer(f"Шаг 2/6. Откуда: {city}. Куда едем?", reply_markup=menu.cities_keyboard(cities))


@router.message(BookingStates.to_city, F.text)
async def got_to_city(message: Message, state: FSMContext, service: RailwayService) -> None:
    try:
        city = validate_city(message.text)
    except InputError as error:
        await message.answer(f"⚠️ {error}")
        return
    data = await state.get_data()
    if city.lower() == data["from_city"].lower():
        await message.answer("⚠️ Город назначения должен отличаться от города отправления.")
        return
    trains = await service.search(data["from_city"], city)
    if not trains:
        await message.answer(f"Поездов {data['from_city']} → {city} не найдено. Введите другой город или /cancel.")
        return
    await state.update_data(to_city=city)
    await state.set_state(BookingStates.choose_train)
    await message.answer(f"Найдено поездов: {len(trains)}", reply_markup=menu.cancel_keyboard())
    await message.answer("Шаг 3/6. Выберите поезд:", reply_markup=trains_keyboard(trains, action="book"))


@router.callback_query(TrainCallback.filter(F.action == "book"))
async def choose_train(callback: CallbackQuery, callback_data: TrainCallback, state: FSMContext,
                       service: RailwayService) -> None:
    """Также срабатывает с кнопки «Купить» в расписании — сразу переходим к выбору вагона."""
    try:
        options = await service.available_types(callback_data.train_id)
        train = await service.get_train(callback_data.train_id)
    except BookingError as error:
        await callback.answer(str(error), show_alert=True)
        return
    if not options:
        await callback.answer("Свободных мест нет", show_alert=True)
        return
    await state.update_data(train_id=train.id)
    await state.set_state(BookingStates.choose_wagon)
    await callback.message.answer(f"{train_text(train)}\n\nШаг 4/6. Выберите тип вагона:",
                                  reply_markup=wagons_keyboard(options))
    await callback.answer()


@router.callback_query(BookingStates.choose_wagon, WagonCallback.filter())
async def choose_wagon(callback: CallbackQuery, callback_data: WagonCallback, state: FSMContext,
                       service: RailwayService) -> None:
    data = await state.get_data()
    wagon_type = WagonType(callback_data.wagon_type)
    free = await service.free_seats(data["train_id"], wagon_type)
    await state.update_data(wagon_type=wagon_type.value)
    await state.set_state(BookingStates.choose_seat)
    preview = ", ".join(map(str, free[:30])) + (" …" if len(free) > 30 else "")
    await callback.message.answer(f"Шаг 5/6. {wagon_type.title}. Свободные места: {preview}\nВведите номер места:")
    await callback.answer()


@router.message(BookingStates.choose_seat, F.text)
async def choose_seat(message: Message, state: FSMContext, service: RailwayService) -> None:
    data = await state.get_data()
    wagon_type = WagonType(data["wagon_type"])
    train = await service.get_train(data["train_id"])
    try:
        seat = validate_seat(message.text, train.capacity(wagon_type))
    except InputError as error:
        await message.answer(f"⚠️ {error}")
        return
    if seat not in await service.free_seats(train.id, wagon_type):
        await message.answer("⚠️ Это место уже занято, выберите другое.")
        return
    await state.update_data(seat=seat)
    await state.set_state(BookingStates.passenger_name)
    await message.answer("Шаг 6/6. Введите фамилию и имя пассажира:")


@router.message(BookingStates.passenger_name, F.text)
async def passenger_name(message: Message, state: FSMContext, service: RailwayService) -> None:
    try:
        name = validate_passenger_name(message.text)
    except InputError as error:
        await message.answer(f"⚠️ {error}")
        return
    await state.update_data(passenger_name=name)
    await state.set_state(BookingStates.confirm)
    data = await state.get_data()
    train = await service.get_train(data["train_id"])
    wagon_type = WagonType(data["wagon_type"])
    await message.answer(f"Проверьте данные:\n{train_text(train)}\nВагон: {wagon_type.title}, место {data['seat']}\n"
                         f"Пассажир: {name}\nК оплате: {train.price(wagon_type):.2f} ₽",
                         reply_markup=confirm_keyboard())


@router.callback_query(BookingStates.confirm, ConfirmCallback.filter())
async def confirm(callback: CallbackQuery, callback_data: ConfirmCallback, state: FSMContext,
                  service: RailwayService, user: User) -> None:
    data = await state.get_data()
    await state.clear()
    if callback_data.answer != "yes":
        await callback.message.answer("Покупка отменена.", reply_markup=menu.main_menu())
        await callback.answer()
        return
    try:
        ticket = await service.book(user, data["train_id"], WagonType(data["wagon_type"]), data["seat"],
                                    data["passenger_name"])
    except BookingError as error:
        await callback.message.answer(f"⚠️ {error}", reply_markup=menu.main_menu())
    else:
        await callback.message.answer("✅ Билет оформлен!\n\n" + ticket_text(ticket), reply_markup=menu.main_menu())
    await callback.answer()


@router.message(StateFilter(BookingStates), ~F.text)
async def not_text(message: Message) -> None:
    """Пользователь прислал фото/стикер и т. п. посреди сценария."""
    await message.answer("⚠️ Пожалуйста, отправьте текст или нажмите кнопку. /cancel — отменить покупку.")


@router.callback_query(StateFilter(None), WagonCallback.filter())
@router.callback_query(StateFilter(None), ConfirmCallback.filter())
async def stale_button(callback: CallbackQuery) -> None:
    await callback.answer("Эта кнопка устарела. Начните покупку заново: /buy", show_alert=True)
