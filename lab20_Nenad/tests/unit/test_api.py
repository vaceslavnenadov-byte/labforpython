def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "healthy" and body["database"] == "up"


def test_create_ride_and_cache(client, driver):
    ride = client.post("/rides", json={"passenger": "Иван", "driver_id": driver["id"], "pickup": "Тверская",
                                       "destination": "Внуково", "distance_km": 28})
    assert ride.status_code == 201 and ride.json()["cost"] == 491
    first = client.get(f"/rides/{ride.json()['id']}")
    second = client.get(f"/rides/{ride.json()['id']}")
    assert first.headers["X-Cache"] == "MISS" and second.headers["X-Cache"] == "HIT"


def test_status_transitions_and_invalidation(client, driver):
    ride_id = client.post("/rides", json={"passenger": "Иван", "driver_id": driver["id"], "pickup": "А1",
                                          "destination": "Б1", "distance_km": 5}).json()["id"]
    client.get(f"/rides/{ride_id}")
    assert client.patch(f"/rides/{ride_id}/status", json={"status": "completed"}).status_code == 409
    client.patch(f"/rides/{ride_id}/status", json={"status": "in_progress"})
    client.patch(f"/rides/{ride_id}/status", json={"status": "completed"})
    response = client.get(f"/rides/{ride_id}")
    assert response.headers["X-Cache"] == "MISS" and response.json()["status"] == "completed"
    assert client.get("/stats").json()["completed_rides"] == 1


def test_errors(client, driver):
    assert client.get("/rides/999").status_code == 404
    assert client.post("/rides", json={"passenger": "И", "driver_id": 1}).status_code == 422
    assert client.post("/drivers", json={"full_name": "Дубль", "car_plate": "А001АА777",
                                         "car_class": "comfort"}).status_code == 409
    ride = {"passenger": "Иван", "driver_id": driver["id"], "pickup": "А1", "destination": "Б1", "distance_km": 5}
    client.post("/rides", json=ride)
    assert client.post("/rides", json=ride).status_code == 409          # у водителя уже есть активная поездка
