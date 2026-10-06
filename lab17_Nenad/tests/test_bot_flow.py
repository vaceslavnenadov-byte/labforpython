"""Сквозные тесты: апдейты проходят через Dispatcher, middleware, фильтры и FSM."""

from aiogram.methods import AnswerCallbackQuery, SendMessage

from keyboards.inline import ConfirmCallback, TrainCallback, WagonCallback
from tests.conftest import ADMIN_ID, BotHarness


async def test_start_shows_main_menu(harness):
    answers = await harness.send("/start")
    assert "Здравствуйте" in harness.texts(answers)
    assert answers[0].reply_markup.keyboard[0][0].text == "🚆 Расписание"


async def test_full_purchase_fsm(harness):
    await harness.send("/buy")
    assert "Куда" in harness.texts(await harness.send("Москва"))
    answers = await harness.send("Санкт-Петербург")
    train_buttons = answers[-1].reply_markup.inline_keyboard
    assert len(train_buttons) == 2
    await harness.press(TrainCallback(action="book", train_id=1).pack())
    assert "Свободные места" in harness.texts(await harness.press(WagonCallback(wagon_type="sv").pack()))
    assert "с 1 по 18" in harness.texts(await harness.send("100"))                # валидация номера места
    await harness.send("3")
    assert "Проверьте" in harness.texts(await harness.send("тестов иван"))
    final = harness.texts(await harness.press(ConfirmCallback(answer="yes").pack()))
    assert "Билет оформлен" in final and "Тестов Иван" in final
    assert "Ваши билеты (1)" in harness.texts(await harness.send("/mytickets"))


async def test_cancel_and_same_city_validation(harness):
    await harness.send("/buy")
    await harness.send("Казань")
    assert "отличаться" in harness.texts(await harness.send("казань"))
    assert "отменена" in harness.texts(await harness.send("/cancel"))
    assert "Нечего отменять" in harness.texts(await harness.send("/cancel"))


async def test_stale_button_and_unknown_text(harness):
    answers = await harness.press(ConfirmCallback(answer="yes").pack())
    assert isinstance(answers[0], AnswerCallbackQuery) and "устарела" in answers[0].text
    assert "Не понял" in harness.texts(await harness.send("абракадабра"))


async def test_admin_commands_only_for_admin(session_factory):
    user = BotHarness(session_factory, user_id=42)
    assert "Не понял" in user.texts(await user.send("/statistics"))
    admin = BotHarness(session_factory, user_id=ADMIN_ID)
    answer = admin.texts(await admin.send("/statistics"))
    assert "Пользователей" in answer and "Поездов: 16" in answer
