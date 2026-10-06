from tests.conftest import NEW_TRAIN


def test_get_list(client):
    body = client.get("/trains").json()
    assert body["total"] == 8 and len(body["items"]) == 8


def test_get_existing(client):
    train = client.get("/trains/1").json()
    assert train["number"] == "001А" and train["duration_hours"] == 8.0


def test_get_missing_404(client):
    response = client.get("/trains/999")
    assert response.status_code == 404 and response.json()["code"] == "NOT_FOUND"


def test_post_valid_201(client, admin_headers):
    response = client.post("/trains", json=NEW_TRAIN, headers=admin_headers)
    assert response.status_code == 201 and response.json()["id"] == 9


def test_post_invalid_422(client, admin_headers):
    bad = {**NEW_TRAIN, "price": -1, "wagons_count": 0}
    response = client.post("/trains", json=bad, headers=admin_headers)
    assert response.status_code == 422 and "price" in response.json()["error"]


def test_post_arrival_before_departure_422(client, admin_headers):
    bad = {**NEW_TRAIN, "arrival_time": "2026-10-19T08:00:00"}
    assert client.post("/trains", json=bad, headers=admin_headers).status_code == 422


def test_post_duplicate_409(client, admin_headers):
    assert client.post("/trains", json={**NEW_TRAIN, "number": "001А"}, headers=admin_headers).status_code == 409


def test_put(client, admin_headers):
    response = client.put("/trains/2", json={**NEW_TRAIN, "number": "752А"}, headers=admin_headers)
    assert response.status_code == 200 and response.json()["route"] == "Москва - Тверь"


def test_patch_changes_only_given_fields(client, admin_headers):
    patched = client.patch("/trains/3", json={"price": 2600}, headers=admin_headers).json()
    assert patched["price"] == 2600 and patched["route"] == "Москва - Казань"


def test_delete_and_repeat(client, admin_headers):
    assert client.delete("/trains/4", headers=admin_headers).status_code == 204
    assert client.delete("/trains/4", headers=admin_headers).status_code == 404


def test_filtering(client):
    items = client.get("/trains", params={"route": "москва -", "max_price": 3500}).json()["items"]
    assert {t["number"] for t in items} == {"001А", "104В", "727В", "020У"}
    cancelled = client.get("/trains", params={"status": "cancelled"}).json()["items"]
    assert [t["number"] for t in cancelled] == ["727В"]


def test_sorting(client):
    asc = [t["price"] for t in client.get("/trains", params={"sort": "price"}).json()["items"]]
    desc = [t["price"] for t in client.get("/trains", params={"sort": "price", "order": "desc"}).json()["items"]]
    assert asc == sorted(asc) and desc == sorted(desc, reverse=True)
    assert client.get("/trains", params={"sort": "color"}).status_code == 400


def test_pagination(client):
    page = client.get("/trains", params={"skip": 6, "limit": 5, "sort": "number"}).json()
    assert page["total"] == 8 and len(page["items"]) == 2 and page["skip"] == 6


def test_search_by_station(client):
    numbers = {t["number"] for t in client.get("/trains/search", params={"q": "Воронеж"}).json()}
    assert numbers == {"026Ч", "020У"}
    assert client.get("/trains/search", params={"q": "026"}).json()[0]["number"] == "026Ч"


def test_statistics(client):
    stats = client.get("/trains/statistics").json()
    assert stats["total"] == 8 and stats["min_price"] == 1200 and stats["by_status"]["cancelled"] == 1


def test_validation_error_in_query(client):
    assert client.get("/trains", params={"limit": 1000}).status_code == 422
