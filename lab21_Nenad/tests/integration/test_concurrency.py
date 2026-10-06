"""Гонка: два пассажира одновременно заказывают бизнес-класс, а свободен один водитель.
SELECT ... FOR UPDATE SKIP LOCKED гарантирует, что водитель достанется только одному.
Тест выполняется только на PostgreSQL (SQLite не поддерживает блокировки строк)."""

import os
import threading

import pytest

from src.app.cache import Cache
from src.app.exceptions import BusinessRuleException
from src.app.models import Order, User
from src.app.schemas import OrderIn
from src.app.services.services import OrderService

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL", "").startswith("postgresql"),
                                reason="нужен PostgreSQL (TEST_DATABASE_URL)")


def test_one_driver_two_simultaneous_orders(client, app):
    sessions = app.state.session_factory
    with sessions() as db:
        users = [User(email=f"race{i}@taxi.ru", password_hash="x$y", full_name="R", phone="+79000000000")
                 for i in range(2)]
        db.add_all(users)
        db.commit()
        user_ids = [u.id for u in users]

    barrier, results = threading.Barrier(2), []

    def book(user_id):
        with sessions() as db:
            barrier.wait()
            try:
                OrderService(db, Cache()).create(db.get(User, user_id), OrderIn(
                    pickup="Сити", destination="Внуково", distance_km=30, car_class="business"))
                results.append("ok")
            except BusinessRuleException as error:
                results.append(error.error)

    threads = [threading.Thread(target=book, args=(uid,)) for uid in user_ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == ["NO_FREE_DRIVERS", "ok"]
    with sessions() as db:
        assert db.query(Order).count() == 1
