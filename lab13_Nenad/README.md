# ЛР №13 — MongoDB и Redis

**Вариант 10. Железная дорога — поезда.** MongoDB хранит документы поездов; Redis — расписание (ближайшие отправления),
доступные места и кэш карточки поезда.

```
CLI (app/main.py) → TrainService ─┬─► MongoRepository → MongoDB (коллекция railway.trains)
                                  └─► RedisCache      → Redis
```

## Запуск
```bash
pip install -r requirements.txt
docker compose up -d              # MongoDB + Redis
python -m app.main                # при пустой коллекции загружаются 24 документа
python -m app.main --mock         # без серверов: mongomock + fakeredis
python -m app.main --mock-mongo   # настоящий Redis + mongomock
python -m pytest -v               # 14 тестов (mongomock + fakeredis)
```

## Документ MongoDB
```json
{
  "_id": 9, "number": "108К", "name": "Красная стрела", "category": "скорый",
  "status": "scheduled", "base_price": 3200.0, "version": 0,
  "route": {"from": {"station": "Москва Ленинградская", "city": "Москва"},
            "to":   {"station": "Санкт-Петербург Главный", "city": "Санкт-Петербург"}},
  "stops": [{"station": "Москва Ленинградская", "city": "Москва", "arrival": null, "departure": "2026-10-12T14:00"},
            {"station": "Санкт-Петербург Главный", "city": "Санкт-Петербург", "arrival": "2026-10-12T22:00", "departure": null}],
  "wagons": [{"number": 1, "type": "coupe", "seats": 36, "booked": [1, 2, 3]}],
  "cities": ["Москва", "Санкт-Петербург"],
  "departure_time": ISODate("2026-10-12T14:00"), "arrival_time": ISODate("2026-10-12T22:00"),
  "total_seats": 90, "free_seats": 18
}
```
Простые поля, вложенный объект `route`, массивы `stops`, `wagons`, `cities`, поле-статус `status`/`category`.

## Запросы (13)
| № | Запрос | Тип |
|---|---|---|
| 1 | `{"status": s}` | фильтр |
| 2 | `{"base_price": {"$gte": a, "$lte": b}}` | фильтр |
| 3 | `{"free_seats": {"$gte": n}, "status": "scheduled"}` | фильтр, несколько условий |
| 4 | `{"route.from.city": a, "route.to.city": b}` + sort | **вложенное поле** |
| 5 | `{"cities": city}` | **элемент массива** |
| 6 | `{"wagons.type": t}` | массив вложенных документов |
| 7 | sort `departure_time` | сортировка |
| 8 | sort `base_price` + `limit(n)` | сортировка + ограничение |
| 9 | диапазон дат отправления | фильтр |
| 10 | `$group` по статусу | **агрегация** |
| 11 | `$match` + `$group` по категории (avg/min/max) | **агрегация** |
| 12 | `$unwind wagons` + `$group` по типу вагона | **агрегация** |
| 13 | TOP-3 направлений (`$group` + `$sort` + `$limit`) | агрегация (доп. задание 2) |

Индексы: `number` (unique — поиск по номеру, защита от дублей), составной `route.from.city + route.to.city`
(запрос 4), multikey `cities` (запрос 5), `departure_time` (запросы 7, 9).

## Redis (6 структур, 15+ операций)
| Ключ | Тип | Операции | Назначение |
|---|---|---|---|
| `train:{id}` | String | SET EX, GET, DEL, TTL | кэш карточки поезда (TTL 120 с) |
| `train:{id}:seats` | Hash | HSET, HGETALL, EXPIRE, DEL | свободные места по вагонам |
| `departures` | Sorted Set | ZADD, ZREM, ZRANGEBYSCORE | ближайшие отправления (score = время) |
| `search:recent` | List | LPUSH, LTRIM, LRANGE | последние поиски |
| `trains:active` | Set | SADD, SREM, SMEMBERS | поезда, по которым идёт продажа |
| `stats:cache_hit/miss` | String | INCR, GET | счётчики попаданий |
| `lock:train:{id}` | String | SET NX EX | защита от cache stampede |
| `trains.events` | Pub/Sub | PUBLISH | события train.created / updated / deleted |

**Cache-Aside:** GET → Redis (hit) → иначе MongoDB → запись в Redis. При изменении/удалении/бронировании
ключи `train:{id}` и `train:{id}:seats` удаляются, следующий запрос снова идёт в MongoDB (тест `test_cache_aside_flow_with_invalidation`).

Бронирование места — оптимистическая блокировка по полю `version` (обновление одного документа атомарно).

## Benchmark
В среде, где выполнялась работа, сервер MongoDB установить было нельзя (загрузка заблокирована), поэтому замер
выполнен для **mongomock (в памяти процесса) против настоящего Redis по TCP**:

| Запросов | MongoDB (mongomock), с | Redis, с |
|---|---|---|
| 100 | 0.0064 | 0.0116 |
| 1 000 | 0.0646 | 0.1008 |
| 10 000 | 0.6716 | 1.0278 |

Почему так: mongomock — это словари Python в том же процессе, без сети и диска, а Redis — отдельный сервер, каждый GET
идёт по TCP (~100 мкс). С настоящей MongoDB (сетевой запрос + поиск по индексу + BSON-декодирование большого
документа) Redis обычно быстрее, особенно для часто читаемых данных. Замер нужно повторить командой меню 10 после
`docker compose up -d`.

## Что где хранится
* MongoDB — полные документы поездов: гибкая структура, вложенные маршруты и вагоны читаются одним запросом.
* Redis — то, что читается часто и может кратко устаревать: расписание ближайших отправлений, свободные места,
  карточки поездов; очереди/счётчики/события.
