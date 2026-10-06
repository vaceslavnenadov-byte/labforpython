"""Создание маршрута, поиск рейсов, наличие мест (Repository заменён Mock-объектом)."""

from datetime import datetime

import pytest

from src.exceptions import NotFoundError, ValidationError
from tests.conftest import DEPARTURE


def test_create_route_with_valid_data(service, routes_repo):
    # Arrange — фикстуры; Act
    route = service.create_route("001А", "Москва", "Казань", DEPARTURE, 36, 2400)
    # Assert
    assert route.id == 10 and route.to_city == "Казань"
    routes_repo.add.assert_called_once()
    routes_repo.exists.assert_called_once_with("001А", DEPARTURE)


@pytest.mark.parametrize("number, a, b, seats, price, message", [
    ("", "Москва", "Казань", 10, 100, "Номер"),
    ("001А", "Москва", "москва", 10, 100, "различаться"),
    ("001А", "Москва", "Казань", 0, 100, "мест"),            # граница: 0
    ("001А", "Москва", "Казань", 1001, 100, "мест"),         # граница: максимум + 1
    ("001А", "Москва", "Казань", 10, 0, "Цена"),
    ("001А", " ", "Казань", 10, 100, "Города"),             # пустая строка
])
def test_create_route_validation(service, routes_repo, number, a, b, seats, price, message):
    with pytest.raises(ValidationError, match=message):
        service.create_route(number, a, b, DEPARTURE, seats, price)
    routes_repo.add.assert_not_called()


@pytest.mark.parametrize("seats", [1, 1000])                 # граничные допустимые значения
def test_create_route_boundary_seats(service, seats):
    assert service.create_route("002А", "Москва", "Тверь", DEPARTURE, seats, 500).seats == seats


def test_create_route_in_past_rejected(service):
    with pytest.raises(ValidationError, match="будущем"):
        service.create_route("001А", "Москва", "Казань", datetime(2020, 1, 1), 10, 100)


def test_duplicate_route_rejected(service, routes_repo):
    routes_repo.exists.return_value = True
    with pytest.raises(ValidationError, match="уже существует"):
        service.create_route("001А", "Москва", "Казань", DEPARTURE, 10, 100)


def test_get_missing_route(service, routes_repo):
    routes_repo.find_by_id.return_value = None
    with pytest.raises(NotFoundError):
        service.get_route(99)
    routes_repo.find_by_id.assert_called_once_with(99)


def test_free_seats(service, tickets_repo):
    tickets_repo.taken_seats.return_value = {2}
    assert service.free_seats(1) == [1, 3]
    assert service.has_free_seats(1) is True


def test_search_skips_full_routes(service, routes_repo, tickets_repo, route):
    routes_repo.search.return_value = [route]
    tickets_repo.taken_seats.return_value = {1, 2, 3}        # мест нет
    assert service.search("Москва", "Санкт-Петербург") == []
    assert service.search("Москва", "Санкт-Петербург", only_available=False) == [route]
    routes_repo.search.assert_called_with("Москва", "Санкт-Петербург", None)
