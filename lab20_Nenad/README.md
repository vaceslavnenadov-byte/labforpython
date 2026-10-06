# ЛР №20 — Контейнеризация, CI/CD и эксплуатация

**Вариант 10. Такси**: контейнеры API и базы данных, Redis для кэширования, CI.

## Назначение и архитектура
REST API службы такси (водители, поездки, расчёт стоимости, смена статуса поездки) на FastAPI.
```
docker compose
 ├── app    (taxi-api, FastAPI, порт 8000, /health)  ──► db (PostgreSQL 16, volume postgres_data)
 │                                                    └─► redis (кэш GET /rides/{id}, volume redis_data)
 └── сеть taxi — сервисы обращаются друг к другу по имени: db:5432, redis:6379 (не localhost)
```

## Требования
Docker + Docker Compose; для запуска без Docker — Python 3.11+.

## Быстрый старт
```bash
git clone https://github.com/vaceslavnenadov-byte/labforpython
cd labforpython/lab20_Nenad
cp .env.example .env          # обязательно задать DATABASE_PASSWORD
docker compose up --build
curl localhost:8000/health    # {"status":"healthy","database":"up","cache":"up"}
```
Полезные команды: `docker compose ps`, `docker compose logs -f app`, `docker compose down` (данные БД сохраняются в
volume), `docker compose down -v` (удалить и данные).

## Переменные окружения
| Переменная | Назначение |
|---|---|
| `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD` | подключение к PostgreSQL (или `DATABASE_URL` целиком) |
| `REDIS_URL` | кэш; не задан — кэш выключен |
| `CACHE_TTL`, `LOG_LEVEL`, `APP_ENV` | время жизни кэша, уровень логов, окружение |

Секреты не хранятся в коде: `.env` в `.gitignore` и `.dockerignore`, в CI пароль берётся из GitHub Secrets
(`CI_DB_PASSWORD`, при отсутствии — одноразовый пароль тестовой БД CI).

## Docker
* `Dockerfile` — multi-stage: зависимости ставятся в builder-образе, в итоговый копируются только пакеты и `src/`;
  запуск от непривилегированного пользователя `app`; `HEALTHCHECK` через `healthcheck.py` (в slim-образе нет curl).
* `.dockerignore` — `.git`, `.venv`, `__pycache__`, `.pytest_cache`, `.env`, тесты, локальные БД.
* Сборка вручную: `docker build -t taxi-api .`

| Инструкция | Зачем |
|---|---|
| `FROM python:3.12-slim AS builder` | официальный компактный базовый образ |
| `RUN pip install --prefix=/install` | зависимости ставятся при сборке и кэшируются слоем |
| `COPY --from=builder` | в итоговом образе нет pip-кэша и инструментов сборки |
| `USER app` | процесс не работает от root |
| `HEALTHCHECK` / `CMD` | проверка живости и команда запуска uvicorn |

## API
| Метод | URL | Описание |
|---|---|---|
| GET | /health | состояние API, БД и Redis (503, если БД недоступна) |
| POST/GET | /drivers | создать / список водителей |
| POST | /rides | заказать поездку (стоимость по классу авто) |
| GET | /rides?status=, /rides/{id} | список / поездка (заголовок `X-Cache: HIT/MISS`) |
| PATCH | /rides/{id}/status | created → in_progress → completed, отмена (инвалидирует кэш) |
| GET | /stats | завершённые поездки, выручка |

## Тесты
```bash
pip install -r requirements-dev.txt
ruff check .
pytest --cov=src --cov-report=term-missing --cov-fail-under=70     # 9 unit-тестов (SQLite + fakeredis)
TEST_DATABASE_URL=postgresql+psycopg://taxi:...@localhost:5432/taxi_ci TEST_REDIS_URL=redis://localhost:6379/0 \
  pytest -m integration                                               # интеграционный тест с PostgreSQL и Redis
```
Покрытие ~90 %.

## CI pipeline (`.github/workflows/lab20-ci.yml`)
Запускается при `push` и `pull_request`, если изменились файлы `lab20_Nenad/`:
```
Checkout → Setup Python 3.12 → Install → Lint (ruff) → Pytest + coverage ≥ 70 % (с сервисами PostgreSQL и Redis)
        → Docker build → запуск контейнера с PostgreSQL и проверка /health
```
Если линтер, тесты или порог покрытия не пройдены, job `docker` не выполняется и pipeline помечается как failed.
