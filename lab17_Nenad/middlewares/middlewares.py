"""Собственные middleware."""

import logging
import time
from collections import Counter
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker

from services.railway_service import RailwayService

logger = logging.getLogger("bot")


class LoggingMiddleware(BaseMiddleware):
    """Журналирует пользователя, событие и время обработки; считает популярность команд."""

    def __init__(self) -> None:
        self.counter: Counter = Counter()

    async def __call__(self, handler: Callable[[TelegramObject, dict], Awaitable[Any]],
                       event: TelegramObject, data: dict[str, Any]) -> Any:
        if isinstance(event, Message):
            action = event.text or event.content_type
        elif isinstance(event, CallbackQuery):
            action = event.data.split(":")[0] if event.data else "callback"
        else:
            action = type(event).__name__
        user = getattr(event, "from_user", None)
        self.counter[action] += 1
        data["command_stats"] = self.counter
        start = time.perf_counter()
        try:
            return await handler(event, data)
        finally:
            logger.info("USER %s %s (%.1f ms)", user.id if user else "-", action, (time.perf_counter() - start) * 1000)


class ServiceMiddleware(BaseMiddleware):
    """Открывает сессию БД на время обработки события, регистрирует пользователя и передаёт сервис в handler."""

    def __init__(self, session_factory: async_sessionmaker, admin_ids: frozenset[int]) -> None:
        self.session_factory = session_factory
        self.admin_ids = admin_ids

    async def __call__(self, handler: Callable[[TelegramObject, dict], Awaitable[Any]],
                       event: TelegramObject, data: dict[str, Any]) -> Any:
        async with self.session_factory() as session:
            service = RailwayService(session, self.admin_ids)
            data["service"] = service
            tg_user = data.get("event_from_user")
            if tg_user:
                data["user"] = await service.register_user(tg_user.id, tg_user.full_name, tg_user.username)
            return await handler(event, data)
