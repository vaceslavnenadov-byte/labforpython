"""Inline-клавиатуры и структурированные callback data (prefix:поле:поле)."""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import Ticket, TicketStatus, Train, WagonType


class TrainCallback(CallbackData, prefix="train"):
    action: str          # info | book
    train_id: int


class WagonCallback(CallbackData, prefix="wagon"):
    wagon_type: str


class TicketCallback(CallbackData, prefix="ticket"):
    action: str          # show | rename | return
    ticket_id: int


class ConfirmCallback(CallbackData, prefix="confirm"):
    answer: str          # yes | no


def trains_keyboard(trains: list[Train], action: str = "book") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for train in trains:
        builder.button(text=f"{train.number} · {train.departure:%d.%m %H:%M} · от {train.base_price:.0f} ₽",
                       callback_data=TrainCallback(action=action, train_id=train.id))
    builder.adjust(1)
    return builder.as_markup()


def train_info_keyboard(train_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎫 Купить билет", callback_data=TrainCallback(action="book", train_id=train_id).pack()),
    ]])


def wagons_keyboard(options: list[tuple[WagonType, int, float]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for wagon_type, free, price in options:
        builder.button(text=f"{wagon_type.title}: {price:.0f} ₽ (свободно {free})",
                       callback_data=WagonCallback(wagon_type=wagon_type.value))
    builder.adjust(1)
    return builder.as_markup()


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=ConfirmCallback(answer="yes").pack()),
        InlineKeyboardButton(text="✖️ Отменить", callback_data=ConfirmCallback(answer="no").pack()),
    ]])


def tickets_keyboard(tickets: list[Ticket]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in tickets:
        mark = "" if t.status == TicketStatus.ACTIVE else " (возвращён)"
        builder.button(text=f"№{t.id} · {t.train.number} · {t.train.departure:%d.%m}{mark}",
                       callback_data=TicketCallback(action="show", ticket_id=t.id))
    builder.adjust(1)
    return builder.as_markup()


def ticket_actions_keyboard(ticket: Ticket) -> InlineKeyboardMarkup | None:
    if ticket.status != TicketStatus.ACTIVE:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✏️ Изменить ФИО", callback_data=TicketCallback(action="rename", ticket_id=ticket.id).pack()),
        InlineKeyboardButton(text="↩️ Вернуть", callback_data=TicketCallback(action="return", ticket_id=ticket.id).pack()),
    ]])
