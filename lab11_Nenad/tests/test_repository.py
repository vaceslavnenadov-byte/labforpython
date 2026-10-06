def test_get_all_with_filters(service):
    trains = service.trains.get_all(status="scheduled", max_price=2500, sort="price")
    assert [t["number"] for t in trains] == ["727В", "104В", "105Ж"]


def test_sql_injection_is_harmless(service):
    assert service.trains.search("' OR '1'='1", "x") == []
    assert len(service.trains.get_all()) == 12        # таблица не пострадала


def test_schedule_join(service):
    stops = service.trains.schedule(2)
    assert [s["station"] for s in stops] == ["Москва Ленинградская", "Тверь", "Бологое", "Санкт-Петербург Главный"]
