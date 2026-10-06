# Railway API — ЛР №14 (FastAPI)

**Вариант 10. Железная дорога — поезда (`/trains`).** REST API с CRUD, поиском, фильтрацией, сортировкой,
пагинацией, статистикой, кэшем Redis и JWT-авторизацией.

## Технологии
FastAPI, Pydantic v2, SQLAlchemy 2, PostgreSQL (SQLite для локального запуска), Redis, PyJWT, pytest, Docker Compose.

## Архитектура
```
Client → FastAPI (routers) → TrainService → TrainRepository → SQLAlchemy → PostgreSQL
                                   └──────► Cache (Redis): GET /trains/{id}, TTL, инвалидация
```
`app/routers` — HTTP; `app/schemas` — Pydantic; `app/services` — бизнес-логика; `app/repositories` — запросы к БД;
`app/models` — ORM; `app/database.py`, `app/cache.py`, `app/config.py`, `app/security.py`.

## Установка и запуск
```bash
pip install -r requirements.txt
cp .env.example .env               # без .env используется SQLite ./railway.db и кэш выключен
uvicorn app.main:app --reload
```
Docker: `docker compose up --build` → API на http://localhost:8000.

Swagger UI: http://127.0.0.1:8000/docs, ReDoc: http://127.0.0.1:8000/redoc.

При первом запуске создаются 8 поездов и администратор `admin / admin123`.

## Переменные окружения
`DATABASE_URL`, `REDIS_URL` (не задан — кэш выключен), `CACHE_TTL`, `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `APP_ENV`.

## API
| Method | URL | Назначение | Код |
|---|---|---|---|
| GET | /trains | список: `status`, `route`, `departure_date`, `min_price`, `max_price`, `sort=number\|departure_time\|price\|wagons_count`, `order=asc\|desc`, `skip`, `limit` | 200 / 400 / 422 |
| GET | /trains/{id} | поезд (заголовок `X-Cache: HIT/MISS`) | 200 / 404 |
| POST | /trains | создание (ADMIN) | 201 / 401 / 403 / 409 / 422 |
| PUT | /trains/{id} | полная замена (ADMIN) | 200 / 404 / 422 |
| PATCH | /trains/{id} | частичное изменение (ADMIN) | 200 / 404 / 422 |
| DELETE | /trains/{id} | удаление (ADMIN) | 204 / 404 |
| GET | /trains/search?q= | поиск по номеру, маршруту, станциям (**async**) | 200 |
| GET | /trains/statistics | количество, средняя/мин/макс цена, средняя длительность, вагоны, по статусам и маршрутам | 200 |
| POST | /auth/register, /auth/login | регистрация, JWT | 201 / 200 / 401 / 409 |
| GET | /profile | текущий пользователь | 200 / 401 |
| GET | /health | состояние | 200 |

Пример:
```bash
curl -X POST localhost:8000/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'
curl -X PATCH localhost:8000/trains/2 -H "Authorization: Bearer <token>" -H 'Content-Type: application/json' -d '{"price": 4300}'
curl "localhost:8000/trains?route=Москва&sort=price&order=desc&limit=3"
```
Ошибки: `{"error": "Train 999 not found", "code": "NOT_FOUND"}`; traceback клиенту не отдаётся.

## Async
`/trains/search` и `/health` объявлены через `async def`. Корутина — функция, выполнение которой можно приостановить на
`await`; event loop в это время обслуживает другие запросы. Синхронный запрос к БД внутри async-обработчика
заблокировал бы цикл, поэтому он вынесен в пул потоков (`run_in_threadpool`). CPU-bound вычисления от `async` не
ускоряются: процессор занят, и переключаться не на что.

## Тесты
`python -m pytest -v` — 21 тест: список, объект, 404, POST корректный/некорректный, 409, PUT, PATCH, DELETE и повторное
удаление, фильтрация, сортировка, пагинация, поиск, статистика, ошибка валидации, cache miss/hit, инвалидация,
401/403, неверный логин, health.

Доп. задания: JWT (1), роли USER/ADMIN (2), BackgroundTasks — журнал аудита (3), Redis Cache-Aside/TTL/инвалидация (5),
расширенная OpenAPI-документация (8), Docker Compose.
