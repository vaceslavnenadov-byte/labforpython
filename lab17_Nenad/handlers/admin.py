"""Команды администратора: доступны только пользователям из ADMIN_IDS."""

from aiogram import Router
from aiogram.filters import BaseFilter, Command
from aiogram.types import Message

from database.models import User
from services.railway_service import RailwayService

router = Router(name="admin")


class AdminFilter(BaseFilter):
    async def __call__(self, message: Message, user: User) -> bool:
        return user.is_admin


router.message.filter(AdminFilter())


@router.message(Command("admin"))
async def admin_help(message: Message) -> None:
    await message.answer("Команды администратора:\n/users — пользователи\n/statistics — статистика бота")


@router.message(Command("users"))
async def users(message: Message, service: RailwayService) -> None:
    rows = [f"{u.telegram_id} — {u.full_name} (@{u.username or '-'}), сообщений: {u.messages_count}"
            for u in await service.users.all()]
    await message.answer("👥 Пользователи:\n" + "\n".join(rows[-30:]))


@router.message(Command("statistics"))
async def statistics(message: Message, service: RailwayService, command_stats) -> None:
    s = await service.statistics(command_stats)
    await message.answer(
        f"📊 Пользователей: {s['users']}\nСообщений: {s['messages']}\nПоездов: {s['trains']}, станций: {s['stations']}\n"
        f"Билетов: {s['all']} (действующих {s['active']}), выручка {s['revenue']:.2f} ₽\n"
        f"Популярное действие: {s.get('popular', '-')}")
