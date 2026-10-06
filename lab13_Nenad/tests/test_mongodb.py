import pytest

from app.models import ValidationError
from app.repository import NotFoundError
from app.seed import generate


def test_documents_loaded_with_nested_and_arrays(service):
    doc = service.repo.get(1)
    assert service.repo.count() == 24
    assert doc["route"]["from"]["city"] == "Москва"            # вложенный объект
    assert isinstance(doc["stops"], list) and isinstance(doc["wagons"], list)


def test_insert_get_update_delete(service):
    data = generate(1)[0] | {"number": "999Я"}
    doc = service.add_train(data)
    assert service.repo.get_by_number("999Я")["_id"] == doc["_id"]
    assert service.update_train(doc["_id"], {"status": "boarding"})["status"] == "boarding"
    service.delete_train(doc["_id"])
    assert service.repo.get(doc["_id"]) is None
    with pytest.raises(NotFoundError):
        service.delete_train(doc["_id"])


def test_validation(service):
    bad = generate(1)[0] | {"number": "998Я", "base_price": -5}
    with pytest.raises(ValidationError):
        service.add_train(bad)
    with pytest.raises(ValueError):
        service.add_train(generate(1)[0])                       # дубликат номера


def test_filter_queries(service):
    assert all(d["status"] == "cancelled" for d in service.repo.by_status("cancelled"))
    assert all(3000 <= d["base_price"] <= 4000 for d in service.repo.by_price(3000, 4000))
    assert all(d["free_seats"] >= 100 for d in service.repo.with_free_seats(100))


def test_nested_and_array_queries(service):
    route = service.repo.by_route("Москва", "Казань")
    assert route and all(d["route"]["to"]["city"] == "Казань" for d in route)
    assert all("Владимир" in d["cities"] for d in service.repo.through_city("Владимир"))
    assert all(w["type"] == "sv" for d in service.repo.with_wagon_type("sv") for w in d["wagons"])


def test_sort_and_limit(service):
    cheapest = service.repo.cheapest(3)
    assert len(cheapest) == 3 and cheapest[0]["base_price"] <= cheapest[-1]["base_price"]
    times = [d["departure_time"] for d in service.repo.sorted_by_departure()]
    assert times == sorted(times)


def test_aggregations(service):
    by_status = {row["_id"]: row["trains"] for row in service.repo.count_by_status()}
    assert sum(by_status.values()) == 24
    seats = {row["_id"]: row["seats"] for row in service.repo.seats_by_wagon_type()}
    assert seats["sv"] == 18 * 15


def test_book_seat_atomic(service):
    doc = service.repo.get(10)
    wagon = doc["wagons"][0]
    seat = wagon["seats"]                                       # последнее место точно свободно
    booked = service.book_seat(10, wagon["number"], seat)
    assert booked["free_seats"] == doc["free_seats"] - 1
    with pytest.raises(ValueError):
        service.book_seat(10, wagon["number"], seat)            # повторно — нельзя
