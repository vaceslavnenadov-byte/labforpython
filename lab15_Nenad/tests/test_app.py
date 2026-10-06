import re

import pytest

from app import create_app
from app.config import TestConfig

NEW_TRIP = {"client_id": 1, "driver_id": 3, "pickup": "Тверская, 7", "destination": "Внуково",
            "distance_km": 30, "duration_min": 40}


@pytest.fixture
def client():
    app = create_app(TestConfig)
    return app.test_client()


def csrf(client) -> str:
    html = client.get("/trips/create").get_data(as_text=True)
    return re.search(r'name="csrf_token" value="(\w+)"', html).group(1)


# ---------- HTML ----------
def test_index_page(client):
    html = client.get("/").get_data(as_text=True)
    assert "Служба такси" in html and "поездок" in html


def test_list_search_filter_sort_pagination(client):
    assert "Шереметьево" in client.get("/trips?q=шереметьево").get_data(as_text=True)
    html = client.get("/trips?status=cancelled").get_data(as_text=True)
    assert html.count('class="status cancelled"') == 1
    business = client.get("/trips?car_class=business&sort=cost&order=asc").get_data(as_text=True)
    assert "Бизнес" in business and "Эконом</td>" not in business
    assert "<b>2</b>" in client.get("/trips?page=2").get_data(as_text=True)


def test_detail_and_related_links(client):
    html = client.get("/trips/1").get_data(as_text=True)
    assert "Поездка №1" in html and "/drivers/1" in html and "/clients/1" in html


def test_create_edit_delete_via_forms(client):
    token = csrf(client)
    response = client.post("/trips/create", data={**NEW_TRIP, "csrf_token": token}, follow_redirects=True)
    assert "создана" in response.get_data(as_text=True)
    response = client.post("/trips/11/edit", data={**NEW_TRIP, "status": "completed", "csrf_token": token},
                           follow_redirects=True)
    assert "Завершена" in response.get_data(as_text=True)
    response = client.post("/trips/11/delete", data={"csrf_token": token}, follow_redirects=True)
    assert "удалена" in response.get_data(as_text=True)


def test_form_validation_message(client):
    token = csrf(client)
    html = client.post("/trips/create", data={**NEW_TRIP, "distance_km": -3, "csrf_token": token}).get_data(as_text=True)
    assert "положительным" in html


def test_csrf_required(client):
    assert client.post("/trips/create", data=NEW_TRIP).status_code == 400


def test_custom_404_page(client):
    response = client.get("/trips/999")
    assert response.status_code == 404
    assert client.get("/no-such-page").status_code == 404 and "404" in client.get("/x").get_data(as_text=True)


def test_duplicate_driver_conflict_message(client):
    token = csrf(client)
    html = client.post("/drivers", data={"full_name": "Дубль", "phone": "+79002220001", "car_model": "Lada",
                                         "car_plate": "Х000ХХ77", "car_class": "economy", "csrf_token": token},
                       follow_redirects=True).get_data(as_text=True)
    assert "уже существует" in html


# ---------- REST API ----------
def test_api_crud(client):
    created = client.post("/api/trips", json=NEW_TRIP)
    assert created.status_code == 201 and created.get_json()["cost"] == 99 + 14 * 30 + 6 * 40
    trip_id = created.get_json()["id"]
    assert client.patch(f"/api/trips/{trip_id}", json={"distance_km": 10}).get_json()["distance_km"] == 10
    assert client.put(f"/api/trips/{trip_id}", json={**NEW_TRIP, "driver_id": 1}).get_json()["car_class"] == "business"
    assert client.delete(f"/api/trips/{trip_id}").status_code == 204
    assert client.get(f"/api/trips/{trip_id}").status_code == 404


def test_api_errors(client):
    assert client.post("/api/trips", json={"pickup": "x"}).status_code == 400
    assert client.post("/api/trips", json={**NEW_TRIP, "driver_id": 99}).status_code == 404
    assert client.delete("/api/trips/8").status_code == 409          # поездка в пути
    assert client.get("/api/trips?status=flying").status_code == 400


def test_api_list_and_drivers(client):
    body = client.get("/api/trips?status=completed&sort=cost&order=desc").get_json()
    costs = [t["cost"] for t in body["items"]]
    assert body["total"] == 6 and costs == sorted(costs, reverse=True)
    assert len(client.get("/api/drivers").get_json()) == 4
