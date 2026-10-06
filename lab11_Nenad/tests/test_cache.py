def test_cache_aside_hit_and_miss(service):
    assert service.get_train(1)["source"] == "database"     # cache miss
    assert service.get_train(1)["source"] == "cache"        # cache hit


def test_schedule_ttl(service, cache):
    first = service.schedule(3)
    assert first["source"] == "database"
    assert 0 < cache.ttl("train:3:schedule") <= 60
    assert service.schedule(3)["source"] == "cache"


def test_invalidation_after_update(service):
    service.get_train(1)
    service.update_train(1, {"base_price": 3333}, partial=True)
    fresh = service.get_train(1)
    assert fresh["base_price"] == 3333


def test_redis_structures(service, cache):
    service.search("Москва", "Казань")
    service.get_train(5)
    assert cache.search_history() == ["Москва -> Казань"]
    assert cache.popular()[0][0] == "104В"
    assert cache.count_request() == 1
