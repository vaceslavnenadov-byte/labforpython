from datetime import datetime


def test_cache_aside_flow_with_invalidation(service):
    _, source = service.get_train(7)
    assert source == "mongodb"                                  # 1. MongoDB
    _, source = service.get_train(7)
    assert source == "redis"                                    # 2–3. затем Redis
    service.update_train(7, {"base_price": 9999})               # 4–5. изменение и инвалидирование
    doc, source = service.get_train(7)
    assert source == "mongodb" and doc["base_price"] == 9999    # 6–7. снова MongoDB, свежие данные
    assert service.get_train(7)[1] == "redis"


def test_ttl_is_set(service, redis_client):
    service.get_train(3)
    assert 0 < redis_client.ttl("train:3") <= 60


def test_hash_seats_and_counters(service):
    seats, source = service.available_seats(4)
    assert source == "mongodb"
    seats_again, source = service.available_seats(4)
    assert source == "redis" and seats == seats_again
    stats = service.cache.stats()
    assert stats["misses"] >= 1 and stats["hits"] >= 0


def test_sorted_set_list_and_set(service):
    nearest = service.nearest_departures(datetime(2026, 10, 12), limit=3)
    assert [n for n, _ in nearest] == ["106Ж", "107И", "108К"]
    service.search("Москва", "Сочи")
    assert service.cache.recent_searches() == ["Москва → Сочи"]
    assert "100А" not in service.cache.active_trains()          # поезд уже отправился


def test_pubsub_events(service, redis_client):
    pubsub = redis_client.pubsub()
    pubsub.subscribe("trains.events")
    pubsub.get_message(timeout=1)                               # подтверждение подписки
    service.update_train(2, {"name": "Сапсан-2"})
    message = pubsub.get_message(timeout=1)
    assert message and '"train.updated"' in message["data"]


def test_stampede_lock(service):
    assert service.cache.acquire_lock(1) is True
    assert service.cache.acquire_lock(1) is False               # второй запрос не идёт в MongoDB
    service.cache.release_lock(1)
