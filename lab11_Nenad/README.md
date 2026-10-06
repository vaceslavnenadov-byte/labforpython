# ЛР №11 — Реляционные и нереляционные БД, кэширование, CDN

**Вариант 10. Железная дорога.** Основная сущность — `Train`; в Redis кэшируется **состояние расписания**;
через CDN раздаются **схемы вагонов**.

```
Client ─HTTP─► Flask API ─► RailwayService ─┬─► TrainRepository/TicketRepository ─► SQLite (railway.db, чистый SQL)
                                             ├─► Redis (кэш расписания, популярные поезда, история поиска)
Browser ───────────────────────────────────────► CDN edge (:8081) ─► origin (:8080)  — SVG-схемы, CSS, JS
```

## Запуск
```bash
pip install -r requirements.txt
redis-server                       # необязательно: без Redis API работает, кэш отключается
python app.py                      # API: http://127.0.0.1:5000 (БД создаётся из sql/schema.sql + sql/seed.sql)
python run_queries.py              # все 18 SQL-запросов из sql/queries.sql с результатами
python benchmark.py                # SQLite vs Redis, график benchmark.png
cd cdn && python origin_server.py & python edge_server.py & python check_cdn.py
python -m pytest -v                # 16 тестов (Redis в тестах — fakeredis)
```

## База данных (ER)
```
stations 1───N route_stops N───1 trains 1───N wagons 1───N tickets N───1 passengers
           (N:M «поезд — станция» через route_stops)
```
* 6 таблиц, PK во всех, 6 внешних ключей, `NOT NULL`, `UNIQUE`, `CHECK`.
* 12 поездов, 12 станций, 18 вагонов, 8 пассажиров, 12 билетов.
* Индексы: `idx_tickets_active_seat` (частичный уникальный — одно место = один действующий билет; ускоряет поиск
  свободных мест), `idx_route_stops_station` (поиск «откуда — куда», см. EXPLAIN в запросе 18),
  `idx_tickets_passenger` (история поездок). Индекс на каждом поле не создаётся: он замедляет INSERT/UPDATE и занимает место.
* Все запросы параметризованы (`?`), имена столбцов для сортировки — только из белого списка → SQL injection невозможна
  (тест `test_sql_injection_is_harmless`).
* Транзакция: `POST /tickets` — BEGIN → проверка поезда/вагона/места → поиск или создание пассажира → INSERT билета → COMMIT;
  при любой ошибке ROLLBACK (тест: новый пассажир не остаётся в БД, если место занято).

## API
| Метод | URL | Назначение |
|---|---|---|
| GET | /trains?status=&min_price=&max_price=&sort=number\|price\|name&order= | список |
| GET/PUT/PATCH/DELETE | /trains/{id} | CRUD (GET — cache-aside, изменения инвалидируют кэш) |
| POST | /trains | создание |
| GET | /trains/{id}/schedule | расписание (Redis, TTL 60 с, поле `source`: cache/database) |
| GET | /trains/{id}/free-seats | свободные места по вагонам |
| GET | /search?from=Москва&to=Владимир | поиск поездов по маршруту (история поиска — Redis LIST) |
| POST | /tickets | покупка билета (транзакция) |
| POST | /tickets/{id}/return | возврат |
| GET | /stats/cache | популярные поезда (ZSET), история поиска (LIST), счётчик запросов (INCR) |

Redis-операции: `SET … EX`, `GET`, `DEL`, `TTL`, `INCR`, `LPUSH`, `LTRIM`, `LRANGE`, `EXPIRE`, `ZINCRBY`, `ZREVRANGE`.

## CDN
Внешний CDN недоступен, поэтому используется разрешённая локальная имитация: `origin_server.py` (задержка 150 мс
имитирует удалённость, `Cache-Control`, `ETag`) и `edge_server.py` (кэш edge, заголовки `X-Cache: HIT/MISS`, `Age`, `/purge`).

| Ресурс | Origin, мс | CDN 1-й запрос | CDN 2-й запрос | Cache-Control |
|---|---|---|---|---|
| images/*.svg | ~154 | ~158 (MISS) | ~3 (HIT) | public, max-age=3600 |
| css/style.v1.css, v2 | ~154 | ~157 (MISS) | ~3 (HIT) | public, max-age=31536000, immutable |
| js/app.js | ~154 | ~157 (MISS) | ~4 (HIT) | public, max-age=300 |

Cache busting: `style.v1.css` → `style.v2.css` — новое имя = новый URL, поэтому кэш с «вечным» `max-age` не мешает обновлению.

## Benchmark (100 / 1000 / 10000 чтений расписания)
| Запросов | SQLite, с | Redis, с |
|---|---|---|
| 100 | 0.0009 | 0.0097 |
| 1000 | 0.0072 | 0.0897 |
| 10000 | 0.0752 | 0.9449 |

Вывод: здесь SQLite быстрее, потому что база маленькая, лежит в памяти **того же процесса**, а каждый запрос к Redis — это
сетевой обмен по TCP (~90 мкс). Redis выигрывает, когда основная БД — отдельный сервер с тяжёлыми запросами
(PostgreSQL по сети, большие JOIN), и когда кэш общий для нескольких экземпляров API.

## Где хранить данные
| Данные | Где | Почему |
|---|---|---|
| Поезда, вагоны, билеты, пассажиры | SQLite/PostgreSQL | связи, ограничения целостности, транзакции |
| Состояние расписания, популярные поезда, история поиска | Redis | часто читается, допускает кратковременную неактуальность, TTL |
| Схемы вагонов, CSS, JS | CDN | статичны, большие, нужны всем пользователям с минимальной задержкой |

| | PostgreSQL/SQLite | MongoDB | Redis | CDN |
|---|---|---|---|---|
| Назначение | источник истины | гибкие документы | кэш, счётчики, очереди | доставка статики |
| Структура | таблицы, схема | JSON-документы | ключ-значение | файлы |
| Транзакции | ACID | на уровне документа (и многодокументные) | MULTI/EXEC, без отката | нет |
| Когда использовать | связанные данные | вложенные данные с меняющейся структурой | быстрый временный доступ | изображения, JS, CSS |
