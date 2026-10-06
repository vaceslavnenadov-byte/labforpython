import pytest

from services.validation import InputError, validate_city, validate_passenger_name, validate_seat


@pytest.mark.parametrize("text, expected", [("москва", "Москва"), (" Казань ", "Казань"), ("Ростов-на-Дону", "Ростов-на-Дону")])
def test_valid_cities(text, expected):
    assert validate_city(text) == expected


@pytest.mark.parametrize("text", ["", "1", "Москва123", None])
def test_invalid_cities(text):
    with pytest.raises(InputError):
        validate_city(text)


@pytest.mark.parametrize("text, capacity, ok", [("5", 36, True), ("0", 36, False), ("37", 36, False),
                                                 ("двадцать", 36, False), ("36", 36, True)])
def test_seat(text, capacity, ok):
    if ok:
        assert validate_seat(text, capacity) == int(text)
    else:
        with pytest.raises(InputError):
            validate_seat(text, capacity)


def test_passenger_name():
    assert validate_passenger_name("иванов иван") == "Иванов Иван"
    for bad in ("Иванов", "Иванов 123", ""):
        with pytest.raises(InputError):
            validate_passenger_name(bad)
