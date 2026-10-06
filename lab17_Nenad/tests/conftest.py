from datetime import datetime

import pytest
from aiogram import Bot
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, SendMessage, TelegramMethod
from aiogram.types import CallbackQuery, Chat, Message, Update
from aiogram.types import User as TgUser

from bot import build_dispatcher
from database.db import create_engine, create_session_factory, init_models
from database.seed import seed
from services.railway_service import RailwayService

ADMIN_ID = 777


class RecordingSession(BaseSession):
    """Подменяет HTTP-обращения к Telegram: запоминает отправленные ботом сообщения."""

    def __init__(self) -> None:
        super().__init__()
        self.sent: list[TelegramMethod] = []

    async def make_request(self, bot, method, timeout=None):
        self.sent.append(method)
        if isinstance(method, SendMessage):
            return Message(message_id=len(self.sent), date=datetime.now(), text=method.text,
                           chat=Chat(id=method.chat_id, type="private"))
        if isinstance(method, AnswerCallbackQuery):
            return True
        return True

    async def close(self):
        pass

    async def stream_content(self, *args, **kwargs):
        raise NotImplementedError


@pytest.fixture
async def session_factory():
    engine = create_engine("sqlite+aiosqlite://")
    await init_models(engine)
    factory = create_session_factory(engine)
    async with factory() as session:
        await seed(session)
    yield factory
    await engine.dispose()


@pytest.fixture
async def service(session_factory):
    async with session_factory() as session:
        yield RailwayService(session, frozenset({ADMIN_ID}))


_DISPATCHER = None


def shared_dispatcher(session_factory):
    """Роутеры — модульные объекты и подключаются к Dispatcher один раз, поэтому Dispatcher общий,
    а для каждого теста подменяются БД (через middleware) и хранилище FSM."""
    global _DISPATCHER
    if _DISPATCHER is None:
        _DISPATCHER = build_dispatcher(session_factory, frozenset({ADMIN_ID}))
    _DISPATCHER["service_middleware"].session_factory = session_factory
    return _DISPATCHER


class BotHarness:
    """Отправляет боту «входящие» обновления и возвращает тексты ответов."""

    def __init__(self, session_factory, user_id: int = 42) -> None:
        self.session = RecordingSession()
        self.bot = Bot("123456:TEST", session=self.session)
        self.dp = shared_dispatcher(session_factory)
        self.user = TgUser(id=user_id, is_bot=False, first_name="Иван", last_name="Тестов", username="ivan")
        self.counter = 0

    def _chat(self):
        return Chat(id=self.user.id, type="private")

    async def send(self, text: str) -> list[SendMessage]:
        self.counter += 1
        message = Message(message_id=self.counter, date=datetime.now(), chat=self._chat(), from_user=self.user, text=text)
        return await self._feed(Update(update_id=self.counter, message=message))

    async def press(self, data: str) -> list[TelegramMethod]:
        self.counter += 1
        message = Message(message_id=self.counter, date=datetime.now(), chat=self._chat(), text="кнопки")
        callback = CallbackQuery(id=str(self.counter), from_user=self.user, chat_instance="1", data=data, message=message)
        return await self._feed(Update(update_id=self.counter, callback_query=callback))

    async def _feed(self, update: Update) -> list:
        before = len(self.session.sent)
        await self.dp.feed_update(self.bot, update)
        return self.session.sent[before:]

    @staticmethod
    def texts(methods) -> str:
        return "\n".join(m.text for m in methods if isinstance(m, SendMessage))


@pytest.fixture
async def harness(session_factory):
    h = BotHarness(session_factory)
    h.dp.fsm.storage = MemoryStorage()
    return h
