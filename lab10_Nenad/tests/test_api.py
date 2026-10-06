import pytest

from app import create_app

HEADERS = {"X-API-Key": "test-key"}
NEW_TRAIN = {
    "number": "777М", "departure_station": "Москва", "arrival_station": "Тверь",
    "departure_time": "2026-10-20T08:00", "arrival_time": "2026-10-20T10:00",
    "wagons": 5, "seats_per_wagon": 60, "price": 900,
}


@pytest.fixture
def client():
    return create_app(api_key="test-key").test_client()


def test_get_list(client):
    response = client.get("/trains")
    assert response.status_code == 200 and len(response.get_json()) == 6


def test_get_one_and_404(client):
    assert client.get("/trains/1").get_json()["number"] == "001А"
    response = client.get("/trains/999")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Train 999 not found", "code": "TRAIN_NOT_FOUND"}


def test_create(client):
    response = client.post("/trains", json=NEW_TRAIN, headers=HEADERS)
    assert response.status_code == 201
    body = response.get_json()
    assert body["id"] == 7 and body["free_seats"] == 300 and response.headers["Location"] == "/trains/7"


def test_create_invalid_400(client):
    response = client.post("/trains", json={**NEW_TRAIN, "price": -100, "number": ""}, headers=HEADERS)
    assert response.status_code == 400 and response.get_json()["code"] == "VALIDATION_ERROR"


def test_put_and_patch(client):
    assert client.put("/trains/2", json={**NEW_TRAIN, "price": 1000}, headers=HEADERS).get_json()["price"] == 1000
    patched = client.patch("/trains/2", json={"price": 1200}, headers=HEADERS).get_json()
    assert patched["price"] == 1200 and patched["number"] == "777М"


def test_delete_204_then_404(client):
    client.post("/trains", json=NEW_TRAIN, headers=HEADERS)
    assert client.delete("/trains/7", headers=HEADERS).status_code == 204
    assert client.delete("/trains/7", headers=HEADERS).status_code == 404


def test_filter_and_sort(client):
    data = client.get("/trains?from=Москва&sort=price&order=asc").get_json()
    prices = [t["price"] for t in data]
    assert prices == sorted(prices) and all(t["departure_station"] == "Москва" for t in data)


def test_free_seats_endpoint(client):
    data = client.get("/trains/free-seats?min_seats=200").get_json()
    assert {t["number"] for t in data} == {"104В", "002А", "015Е"}


def test_errors_405_401_and_bad_sort(client):
    assert client.post("/trains/1", json={}, headers=HEADERS).status_code == 405
    assert client.post("/trains", json=NEW_TRAIN).status_code == 401
    assert client.get("/trains?sort=color").status_code == 400


def test_pagination(client):
    body = client.get("/trains?page=2&limit=4").get_json()
    assert body["total"] == 6 and len(body["items"]) == 2
