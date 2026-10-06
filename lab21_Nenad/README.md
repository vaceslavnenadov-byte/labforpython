# Лабораторная работа №21 — итоговый проект (уровень B)

**Вариант 10. Такси.** Сущности: пассажир (User), водитель (Driver), автомобиль (Car), заказ (Order).

Стек: **FastAPI + SQLAlchemy 2 + PostgreSQL + Redis + RabbitMQ/Redis Streams + фоновый worker + JWT + Docker Compose + GitHub Actions**.

## Архитектура

```
              ┌──────────── HTTP (JWT) ────────────┐
 клиент ──▶  │ api/ (роутеры, валидация Pydantic)  │
              │ services/ (бизнес-правила)          │──▶ Redis (кэш водителей и статистики)
              │ repositories/ (SQLAlchemy)          │
              └──────────────┬──────────────────────┘
                             │ одна транзакция: заказ + водитель + событие в outbox
                             ▼
                        PostgreSQL ◀──────────────┐
                             │ outbox             │ уведомления (идемпотентно)
                             ▼                    │
                 worker: relay ──▶ RabbitMQ ──▶ worker: consumer
```

```
lab21_Nenad/
├── src/app/
│   ├── main.py            # create_app(), обработчики ошибок, middleware логирования, /health
│   ├── config.py          # настройки только из переменных окружения
│   ├── models.py          # User, Car, Driver, Order, Notification, OutboxEvent
│   ├── schemas.py         # Pydantic-схемы и валидация
│   ├── exceptions.py      # иерархия исключений → {"error", "message"}
│   ├── security.py        # PBKDF2-хэш паролей, JWT
│   ├── cache.py           # Cache-Aside поверх Redis, деградация без Redis
│   ├── events.py          # брокеры: RabbitMQ / Redis Streams / память
│   ├── worker.py          # Transactional Outbox relay + потребитель уведомлений
│   ├── seed.py            # администратор из ENV, тестовый автопарк
│   ├── api/               # auth, fleet (cars/drivers), orders, deps
│   ├── services/          # AuthService, FleetService, OrderService, pricing
│   └── repositories/      # репозитории SQLAlchemy
├── tests/unit|integration # 42 теста, покрытие 93%
├── Dockerfile             # multi-stage, non-root, HEALTHCHECK
├── docker-compose.yml     # api, worker, PostgreSQL, Redis, RabbitMQ (+ volumes, healthchecks)
└── .env.example
```

## Бизнес-правила

1. У пассажира может быть **только один активный заказ** (`assigned` или `in_progress`), иначе `409 ACTIVE_ORDER_EXISTS`.
2. Водитель **назначается автоматически**: свободный, с машиной нужного класса, с наибольшим рейтингом. Строка блокируется (`SELECT … FOR UPDATE SKIP LOCKED`), поэтому два одновременных заказа не получат одного водителя (тест `test_concurrency.py`).
3. **Жизненный цикл заказа:** `assigned → in_progress → completed`, отмена возможна из `assigned` и `in_progress`. Пассажир может отменить заказ только до начала поездки (`409 TRIP_STARTED`). Начать и завершить поездку может только диспетчер (ADMIN). Остальные переходы дают `409 INVALID_TRANSITION`.
4. **Динамическая цена:** тариф класса (подача + ₽/км, с минимальной стоимостью) умножается на коэффициент спроса. Если занято меньше 50% водителей, коэффициент 1.0; от 50% до 80% — 1.2; от 80% — 1.5. Отменённый заказ стоит 0.
5. Нельзя удалить водителя или машину во время поездки и нельзя закрепить одну машину за двумя водителями. Статус `busy` ставится только при назначении заказа.

## API

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| POST | /auth/register | все | регистрация пассажира |
| POST | /auth/login | все | получить JWT |
| GET | /auth/me | USER | текущий пользователь |
| GET/POST/DELETE | /cars | GET — USER, изменение — ADMIN | автомобили |
| GET | /drivers?status=&car_class=&sort=rating\|name | USER | фильтрация и сортировка |
| GET | /drivers/{id} | USER | кэшируется в Redis, заголовок `X-Cache: HIT/MISS` |
| POST/PATCH/DELETE | /drivers | ADMIN | управление водителями |
| POST | /orders/quote | USER | расчёт стоимости с учётом спроса |
| POST | /orders | USER | создать заказ (автоназначение водителя) |
| GET | /orders?status=&q=&sort=&order=&skip=&limit= | USER — свои, ADMIN — все | поиск, сортировка, пагинация |
| GET | /orders/{id} | владелец / ADMIN | заказ (чужой → 404) |
| POST | /orders/{id}/start, /complete | ADMIN | смена статуса |
| POST | /orders/{id}/cancel | владелец / ADMIN | отмена |
| DELETE | /orders/{id} | ADMIN | удалить завершённый заказ |
| GET | /stats | ADMIN | выручка, средний чек, распределения (кэш 30 с) |
| GET | /notifications | USER | уведомления от worker |
| GET | /health | все | состояние БД, Redis и брокера |

Документация Swagger: `http://localhost:8000/docs`.

Все ошибки возвращаются в одном формате:

```json
{"error": "ACTIVE_ORDER_EXISTS", "message": "You already have an active order"}
```

## Асинхронная обработка (Transactional Outbox)

Изменение заказа и событие (`order.assigned`, `order.in_progress`, `order.completed`, `order.cancelled`) записываются **в одной транзакции** в таблицу `outbox`. Worker публикует события в брокер с повторами и помечает их отправленными. Потребитель создаёт уведомление пассажиру. Повторная доставка того же `event_id` игнорируется, то есть обработчик идемпотентен.

## Отказоустойчивость

| Сбой | Поведение |
|---|---|
| Redis недоступен | кэш пропускается, данные берутся из БД, `/health` возвращает `degraded` |
| Брокер недоступен | заказы создаются, события копятся в outbox и отправляются после восстановления |
| Worker остановлен | то же самое: после перезапуска все уведомления доставляются |
| БД недоступна | приложение стартует, `/health` отвечает 503, запросы получают `503 DATABASE_UNAVAILABLE` |

Проверено вживую: при остановленном worker создан и отменён заказ, в outbox было 2 ожидающих события. После запуска worker осталось 0, и пассажир получил оба уведомления.

## Запуск

```bash
# Docker
cp .env.example .env        # задайте пароли
docker compose up --build

# локально (SQLite, кэш и брокер в памяти)
pip install -r requirements-dev.txt
uvicorn src.app.main:app --reload
python -m src.app.worker    # в отдельном терминале

# тесты
pytest --cov=src                                                        # SQLite
TEST_DATABASE_URL=postgresql+psycopg://taxi:***@localhost/taxi_ci pytest  # PostgreSQL (+ тест гонки)
ruff check .
```

## Безопасность

Пароли хранятся в виде PBKDF2-SHA256 со случайной солью. Используется JWT с ограниченным сроком жизни и ролями USER/ADMIN. Секреты и пароль администратора берутся только из переменных окружения. Контейнер работает от непривилегированного пользователя, и пассажир не может получить чужие заказы.

## CI (`.github/workflows/lab21-ci.yml`)

1. `ruff check`.
2. `pytest` на SQLite.
3. `pytest` на PostgreSQL с покрытием не ниже 80%.
4. Сборка Docker-образа.
5. Smoke-тест: compose-стек поднимается, `/health` отвечает 200.
