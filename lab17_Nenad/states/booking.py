from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    """Многошаговый сценарий покупки билета (7 состояний)."""
    from_city = State()
    to_city = State()
    choose_train = State()
    choose_wagon = State()
    choose_seat = State()
    passenger_name = State()
    confirm = State()


class RenameStates(StatesGroup):
    new_name = State()
