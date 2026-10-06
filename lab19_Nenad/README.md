# ЛР №19 — Микросервисная архитектура

**Вариант 10. Такси**: сервисы пассажиров, водителей и заказов (+ уведомления), API Gateway.
Ключевое бизнес-правило варианта — **изменение состояния заказа** (assigned → in_progress → completed / cancelled).

```
                      Client
                        │
                        ▼
                ┌──────────────┐   /api/passengers, /api/drivers, /api/orders, /api/notifications, /status
                │ API Gateway  │   request id, логирование, сводный health check
                └──────┬───────┘
     ┌─────────────────┼──────────────────┬──────────────────────┐
     ▼                 ▼                  ▼                      ▼
Passenger Service  Driver Service    Order Service ──HTTP──► Passenger / Driver (Retry + Circuit Breaker)
     │                 │                  │                 Notification Service
     ▼                 ▼                  ▼                      ▲
passengers DB      drivers DB         orders DB                 │
     ▲                 ▲                  │ OrderCreated,         │
     └──────── Broker (RabbitMQ / Redis Streams) ◄── OrderStatusChanged ┘
```

## Запуск
```bash
docker compose up --build          # 5 сервисов, 3 PostgreSQL, RabbitMQ; шлюз: http://localhost:8000/docs
./run_local.sh                     # без Docker: SQLite в каждом сервисе, Redis Streams как брокер
python -m pytest -v                # 34 теста
```
Остановка сервиса для проверки отказоустойчивости: `docker compose stop passenger-service`.

## Сервисы
| Сервис | Ответственность | БД | API |
|---|---|---|---|
| gateway | единая точка входа, маршрутизация, `/status` | — | `/api/{resource}/...` |
| passenger-service | пассажиры | passengers | CRUD `/passengers` |
| driver-service | водители, их статус, назначение | drivers | CRUD `/drivers`, `POST /drivers/assign`, `POST /drivers/{id}/release`, `PATCH /drivers/{id}/status` |
| order-service | заказы и их жизненный цикл, стоимость | orders | CRUD `/orders`, `PATCH /orders/{id}/status`, `/circuit` |
| notification-service | уведомления пассажирам по событиям | notifications | `GET /notifications?passenger_id=` |

Каждый сервис: свой `/health`, своя БД (**Database per Service**: order-service хранит только `passenger_id`/`driver_id`
и узнаёт о пассажире через HTTP API, а не через SQL к чужой базе). Коды: 200, 201, 204, 400, 404, 409, 422, 503.

## Взаимодействие
**Синхронное (HTTP)** — создание заказа: order-service → `GET /passengers/{id}` → `POST /drivers/assign` → сохранение →
событие `OrderCreated`. Если сохранить заказ не удалось, выполняется **компенсирующее действие** (элемент Saga):
`POST /drivers/{id}/release`.

**Асинхронное (брокер)** — `OrderStatusChanged`:
* driver-service освобождает водителя и считает его поездки;
* passenger-service увеличивает число поездок пассажира;
* notification-service создаёт уведомление (идемпотентно: повторно доставленное событие с тем же `event_id` игнорируется).

Брокер выбирается переменной `BROKER_URL`: `amqp://` — RabbitMQ (fanout exchange `taxi.events`, у каждого сервиса своя
очередь), `redis://` — Redis Streams (consumer group на сервис), `memory://` — для тестов.

## Отказоустойчивость (`common/resilience.py`)
* **Retry**: до 3 попыток, тайм-аут 2 с, экспоненциальная задержка 0.2 → 0.4 с; повторяются только сетевые ошибки и 5xx.
* **Circuit Breaker**: после 3 неудач подряд — OPEN (запросы сразу получают 503 без обращения к сервису);
  через 10 с — HALF_OPEN (один пробный запрос): успех → CLOSED, ошибка → OPEN. Состояние: `GET /orders/circuit`.
* Шлюз не открывает предохранитель на сервис, который сам отвечает 503 из-за своей зависимости (`fail_on_5xx=False`);
  эта ошибка была найдена при сквозной проверке.

Проверка (локально, PostgreSQL + Redis):
```
order attempt 1..4 -> 503
GET /orders/circuit  → {"passenger-service": "OPEN", "driver-service": "CLOSED"}
GET /status          → passenger-service ✗ ... Connection refused; остальные ✓ healthy
order-service WARNING попытка 1/3 не удалась (Connection refused), повтор через 0.2 с
```

## Логи
`2026-10-06 10:39:49 order-service INFO request_id=3f2a9c1b77d0 POST /orders status=201 duration=42ms` —
`X-Request-ID` передаётся от шлюза в сервисы и возвращается клиенту.

## Тесты (34)
| Набор | Что проверяется |
|---|---|
| `tests/test_resilience.py` (6) | Retry с backoff, лимит попыток, состояния Circuit Breaker, клиент сервиса |
| `passenger_service/tests` (7) | CRUD, 409, валидация, 404, health, событие, сохранение в собственной БД (интеграционный) |
| `driver_service/tests` (7) | фильтры, назначение, конкурентное назначение (интеграционный), освобождение, события |
| `order_service/tests` (7) | расчёт стоимости, **взаимодействие сервисов** (3 приложения в памяти), 400/409, жизненный цикл, **недоступность сервиса**: 503 + Retry + OPEN |
| `notification_service/tests` (3) | уведомления по событиям, идемпотентность |
| `gateway/tests` (4) | маршрутизация, неизвестный ресурс, недоступный сервис, `/status`, проброс 5xx |

## Паттерны
| Паттерн | Где |
|---|---|
| API Gateway | `gateway/` |
| Database per Service | 3 PostgreSQL + SQLite у уведомлений |
| Retry, Circuit Breaker | `common/resilience.py`, order-service и gateway |
| Event-Driven | `common/events.py`, события заказа |
| Saga (компенсация) | освобождение водителя при ошибке сохранения заказа |
| Transactional Outbox | не реализован: если брокер недоступен в момент публикации, событие теряется (заказ сохраняется). Решение — писать событие в таблицу outbox в той же транзакции и публиковать отдельным процессом |
| CQRS, Service Discovery, Anti-Corruption Layer | не требуются при таком размере; адреса сервисов задаются переменными окружения (DNS-имена docker compose) |

Недостатки архитектуры: больше инфраструктуры и сетевых вызовов, согласованность данных между сервисами — «в конечном
счёте» (водитель освобождается по событию), сложнее отладка. Для системы такого размера монолит (ЛР 15) был бы проще;
микросервисы оправданы, когда части системы нужно масштабировать и развёртывать независимо.
