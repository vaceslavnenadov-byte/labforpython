import pytest

from exceptions import ConflictError, NotFoundError, ValidationError

TICKET = {"train_id": 1, "wagon": 1, "seat": 3, "full_name": "Тестов Т.Т.", "passport": "9999 111111"}


def test_create_read_update_delete(service):
    train = service.create_train({"number": "999Т", "name": "Тест", "base_price": 1000})
    assert train["source"] == "database"
    updated = service.update_train(train["id"], {"base_price": 1500}, partial=True)
    assert updated["base_price"] == 1500
    service.delete_train(train["id"])
    with pytest.raises(NotFoundError):
        service.get_train(train["id"])


def test_validation(service):
    with pytest.raises(ValidationError):
        service.create_train({"number": "", "base_price": -1})
    with pytest.raises(ConflictError):
        service.create_train({"number": "001А", "base_price": 100})


def test_buy_ticket_transaction_commit(service, db):
    ticket = service.buy_ticket(TICKET)
    assert ticket["price"] == 5760 and ticket["full_name"] == "Тестов Т.Т."
    assert 3 not in service.free_seats(1)[0]["free_seats"]


def test_buy_ticket_rollback_on_taken_seat(service, db):
    before_passengers = db.execute("SELECT COUNT(*) FROM passengers").fetchone()[0]
    with pytest.raises(ConflictError):
        service.buy_ticket({**TICKET, "seat": 1, "passport": "1111 222222"})   # место 1 уже занято
    # новый пассажир не должен остаться в БД — транзакция откатилась
    assert db.execute("SELECT COUNT(*) FROM passengers").fetchone()[0] == before_passengers


def test_cannot_buy_for_cancelled_train(service):
    with pytest.raises(ConflictError):
        service.buy_ticket({**TICKET, "train_id": 12})


def test_search_route(service):
    numbers = [t["number"] for t in service.search("Москва", "Владимир")]
    assert set(numbers) == {"104В", "024Г", "727В"}
    assert service.search("Владимир", "Москва")[0]["number"] == "105Ж"   # обратное направление


def test_return_ticket(service):
    result = service.return_ticket(1)
    assert result["status"] == "returned" and result["refund"] == 5184.0
    with pytest.raises(ConflictError):
        service.return_ticket(1)
