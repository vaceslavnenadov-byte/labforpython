"""API-тесты: полный HTTP-цикл через TestClient (БД — SQLite или PostgreSQL из TEST_DATABASE_URL)."""

from src.app.worker import handle_event, relay_outbox
from tests.conftest import ORDER, register


def test_health(client):
    body = client.get("/health").json()
    assert body == {"status": "ok", "database": "ok", "redis": "ok", "broker": "ok"}


def test_register_validation_and_duplicate(client):
    bad = client.post("/auth/register", json={"email": "bad", "password": "1", "full_name": "X", "phone": "123"})
    assert bad.status_code == 422 and bad.json()["error"] == "VALIDATION_ERROR"
    register(client)
    duplicate = client.post("/auth/register", json={"email": "PASS@taxi.ru", "password": "secret-123",
                                                    "full_name": "Двойник", "phone": "+79001112233"})
    assert duplicate.status_code == 409 and duplicate.json()["error"] == "USER_EXISTS"


def test_login_and_me(client, user_headers):
    assert client.get("/auth/me", headers=user_headers).json()["role"] == "USER"
    wrong = client.post("/auth/login", json={"email": "pass@taxi.ru", "password": "wrong-pass"})
    assert wrong.status_code == 401 and wrong.json()["error"] == "UNAUTHORIZED"


def test_auth_required_and_bad_token(client):
    assert client.get("/orders").status_code == 401
    response = client.get("/orders", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401 and response.json()["message"] == "Invalid token"


def test_user_cannot_manage_fleet(client, user_headers):
    response = client.post("/cars", headers=user_headers,
                           json={"plate": "О777ОО777", "model": "BMW 5", "car_class": "business", "year": 2023})
    assert response.status_code == 403 and response.json()["error"] == "FORBIDDEN"
    assert client.delete("/drivers/1", headers=user_headers).status_code == 403


def test_admin_fleet_crud(client, admin_headers):
    car = client.post("/cars", headers=admin_headers,
                      json={"plate": "О777ОО777", "model": "BMW 5", "car_class": "business", "year": 2023})
    assert car.status_code == 201
    driver = client.post("/drivers", headers=admin_headers, json={
        "full_name": "Пётр Новиков", "phone": "+79005556677", "license_number": "77BB123456",
        "car_id": car.json()["id"]})
    assert driver.status_code == 201 and driver.json()["car"]["plate"] == "О777ОО777"
    driver_id = driver.json()["id"]
    patched = client.patch(f"/drivers/{driver_id}", headers=admin_headers, json={"rating": 4.2})
    assert patched.json()["rating"] == 4.2
    assert client.patch(f"/drivers/{driver_id}", headers=admin_headers, json={"rating": 7}).status_code == 422
    assert client.delete(f"/drivers/{driver_id}", headers=admin_headers).status_code == 204
    assert client.delete(f"/cars/{car.json()['id']}", headers=admin_headers).status_code == 204
    missing = client.get(f"/drivers/{driver_id}", headers=admin_headers)
    assert missing.status_code == 404 and missing.json()["error"] == "DRIVER_NOT_FOUND"


def test_drivers_filter_sort_and_cache(client, user_headers):
    comfort = client.get("/drivers?car_class=comfort&sort=name", headers=user_headers).json()
    assert [d["full_name"] for d in comfort] == ["Анна Кузнецова", "Сергей Волков"]
    by_rating = client.get("/drivers", headers=user_headers).json()
    assert by_rating[0]["full_name"] == "Мария Орлова"
    assert client.get("/drivers?sort=age", headers=user_headers).status_code == 422
    assert client.get("/drivers/1", headers=user_headers).headers["X-Cache"] == "MISS"
    assert client.get("/drivers/1", headers=user_headers).headers["X-Cache"] == "HIT"


def test_quote(client, user_headers):
    body = client.post("/orders/quote", headers=user_headers, json={"distance_km": 10, "car_class": "comfort"}).json()
    assert body == {"car_class": "comfort", "distance_km": 10.0, "surge": 1.0, "price": 339.0}


def test_order_validation(client, user_headers):
    same = client.post("/orders", headers=user_headers, json={**ORDER, "destination": ORDER["pickup"]})
    assert same.status_code == 422 and "must differ" in same.json()["message"]
    assert client.post("/orders", headers=user_headers, json={**ORDER, "distance_km": -1}).status_code == 422
    assert client.post("/orders", headers=user_headers, json={**ORDER, "car_class": "jet"}).status_code == 422


def test_full_order_lifecycle(client, user_headers, admin_headers, app):
    created = client.post("/orders", headers=user_headers, json=ORDER)
    assert created.status_code == 201
    order = created.json()
    assert order["status"] == "assigned" and order["price"] == 239.0
    assert client.get(f"/drivers/{order['driver_id']}", headers=user_headers).json()["status"] == "busy"

    second = client.post("/orders", headers=user_headers, json=ORDER)
    assert second.status_code == 409 and second.json()["error"] == "ACTIVE_ORDER_EXISTS"
    assert client.post(f"/orders/{order['id']}/start", headers=user_headers).status_code == 403

    assert client.post(f"/orders/{order['id']}/start", headers=admin_headers).json()["status"] == "in_progress"
    cancel = client.post(f"/orders/{order['id']}/cancel", headers=user_headers)
    assert cancel.status_code == 409 and cancel.json()["error"] == "TRIP_STARTED"
    done = client.post(f"/orders/{order['id']}/complete", headers=admin_headers).json()
    assert done["status"] == "completed" and done["finished_at"]
    assert client.get(f"/drivers/{order['driver_id']}", headers=user_headers).json()["status"] == "free"

    # фоновый worker: outbox → брокер → уведомления пассажиру
    with app.state.session_factory() as db:
        assert relay_outbox(db, app.state.broker) == 3
        for event in list(app.state.broker.messages):
            handle_event(db, event)
    texts = [n["text"] for n in client.get("/notifications", headers=user_headers).json()]
    assert len(texts) == 3 and "завершена" in texts[0] and "назначен водитель" in texts[-1]


def test_orders_are_private(client, user_headers, admin_headers):
    order_id = client.post("/orders", headers=user_headers, json=ORDER).json()["id"]
    stranger = register(client, "other@taxi.ru", "+79004445566")
    assert client.get(f"/orders/{order_id}", headers=stranger).status_code == 404
    assert client.post(f"/orders/{order_id}/cancel", headers=stranger).status_code == 404
    assert client.get("/orders", headers=stranger).json()["total"] == 0
    assert client.get(f"/orders/{order_id}", headers=admin_headers).status_code == 200


def test_orders_search_pagination_sort(client, user_headers, admin_headers):
    destinations = ["Аэропорт Внуково", "Вокзал Казанский", "Аэропорт Домодедово"]
    for index, destination in enumerate(destinations):
        headers = register(client, f"u{index}@taxi.ru", f"+7900111000{index}")
        order = client.post("/orders", headers=headers, json={**ORDER, "destination": destination,
                                                                "distance_km": 5 + index * 10}).json()
        client.post(f"/orders/{order['id']}/cancel", headers=headers)
    found = client.get("/orders?q=аэропорт&sort=distance&order=asc", headers=admin_headers).json()
    assert found["total"] == 2 and [o["destination"] for o in found["items"]] == ["Аэропорт Внуково",
                                                                                  "Аэропорт Домодедово"]
    page = client.get("/orders?limit=2&skip=2", headers=admin_headers).json()
    assert page["total"] == 3 and len(page["items"]) == 1
    assert client.get("/orders?status=cancelled", headers=admin_headers).json()["total"] == 3
    assert client.get("/orders?limit=500", headers=admin_headers).status_code == 422


def test_delete_order_rules(client, user_headers, admin_headers):
    order_id = client.post("/orders", headers=user_headers, json=ORDER).json()["id"]
    active = client.delete(f"/orders/{order_id}", headers=admin_headers)
    assert active.status_code == 409 and active.json()["error"] == "ORDER_ACTIVE"
    client.post(f"/orders/{order_id}/cancel", headers=user_headers)
    assert client.delete(f"/orders/{order_id}", headers=admin_headers).status_code == 204
    assert client.get(f"/orders/{order_id}", headers=admin_headers).status_code == 404


def test_stats_cached_and_invalidated(client, user_headers, admin_headers):
    assert client.get("/stats", headers=user_headers).status_code == 403
    first = client.get("/stats", headers=admin_headers).json()
    assert first["source"] == "database" and first["completed"] == 0
    assert client.get("/stats", headers=admin_headers).json()["source"] == "cache"
    order_id = client.post("/orders", headers=user_headers, json=ORDER).json()["id"]
    client.post(f"/orders/{order_id}/start", headers=admin_headers)
    client.post(f"/orders/{order_id}/complete", headers=admin_headers)
    stats = client.get("/stats", headers=admin_headers).json()
    assert stats["source"] == "database" and stats["completed"] == 1 and stats["revenue"] == 239.0
    assert stats["completed_by_class"] == {"economy": 1}


def test_request_id_header(client):
    assert client.get("/health", headers={"X-Request-ID": "abc123"}).headers["X-Request-ID"] == "abc123"
