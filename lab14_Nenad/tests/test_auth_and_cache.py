from tests.conftest import NEW_TRAIN


def test_write_requires_token_and_admin(client, user_headers):
    assert client.post("/trains", json=NEW_TRAIN).status_code == 401
    assert client.post("/trains", json=NEW_TRAIN, headers=user_headers).status_code == 403
    assert client.get("/profile", headers=user_headers).json()["role"] == "USER"


def test_bad_login(client):
    assert client.post("/auth/login", json={"username": "admin", "password": "wrong!!"}).status_code == 401


def test_cache_miss_then_hit(client, cache):
    assert client.get("/trains/1").headers["X-Cache"] == "MISS"
    assert client.get("/trains/1").headers["X-Cache"] == "HIT"
    assert 0 < cache.client.ttl("train:1") <= 60


def test_cache_invalidation_on_patch(client, admin_headers):
    client.get("/trains/1")
    client.patch("/trains/1", json={"price": 9999}, headers=admin_headers)
    response = client.get("/trains/1")
    assert response.headers["X-Cache"] == "MISS" and response.json()["price"] == 9999


def test_health(client):
    assert client.get("/health").json()["status"] == "healthy"
