# ЛР №15 — Веб-приложение на Flask

**Вариант 10. Такси** — сущности `Driver`, `Client`, `Trip`: создание поездок (стоимость считается автоматически)
и просмотр истории.

```
Flask (Application Factory)
 ├── Blueprint web  — HTML + Jinja2 (наследование шаблонов от base.html)
 └── Blueprint api  — REST API (JSON)
        ↓
   TaxiService → Repositories → SQLAlchemy → PostgreSQL
```

## Запуск
```bash
pip install -r requirements.txt
cp .env.example .env          # PostgreSQL; без .env используется SQLite taxi_web.db
python run.py                 # http://127.0.0.1:5000 (пустая БД заполняется тестовыми данными)
python -m pytest -v           # 11 тестов
docker compose up --build     # приложение + PostgreSQL
```

## Страницы
| URL | Страница |
|---|---|
| `/` | главная: описание, счётчики, последние поездки |
| `/trips` | список: поиск `q` (адрес/клиент/водитель), фильтры `status`, `car_class`, `driver_id`, сортировка `sort=date\|cost\|distance` + `order`, пагинация `page` |
| `/trips/<id>` | карточка поездки со ссылками на клиента и водителя |
| `/trips/create` | форма создания |
| `/trips/<id>/edit` | форма редактирования (и смена статуса) |
| `POST /trips/<id>/delete` | удаление с подтверждением |
| `/drivers`, `/drivers/<id>` | водители, добавление, история поездок водителя |
| `/clients`, `/clients/<id>` | клиенты, добавление, история поездок клиента |
| 404 | собственный шаблон `404.html` |

## REST API
| Метод | URL | Код |
|---|---|---|
| GET | /api/trips?q=&status=&car_class=&sort=&order=&page= | 200 / 400 |
| GET | /api/trips/<id> | 200 / 404 |
| POST | /api/trips | 201 / 400 / 404 |
| PUT / PATCH | /api/trips/<id> | 200 / 400 / 404 / 409 |
| DELETE | /api/trips/<id> | 204 / 404 / 409 |
| GET | /api/drivers | 200 |

Стоимость = подача + ₽/км + ₽/мин по классу автомобиля водителя (эконом 99/14/6, комфорт 149/19/8, бизнес 299/32/12).

## Прочее
* Конфигурация — переменные окружения (`DATABASE_URL`, `SECRET_KEY`, `PAGE_SIZE`), `.env` не хранится в Git.
* Логирование: запуск, каждый HTTP-запрос с кодом и временем, создание/изменение/удаление поездок, ошибки.
* Ошибки: 400 (валидация, CSRF), 404, 409 (дубликат телефона/номера, удаление поездки в пути), 500 — HTML или JSON.
* Доп. задания: пагинация, CSRF-токен для форм, pytest-тесты, Docker Compose.
