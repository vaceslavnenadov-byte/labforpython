# ЛР №12 — SQLAlchemy ORM и PostgreSQL

**Вариант 10. Такси** — сущности `Client`, `Driver`, `Trip` (+ `Car`). Создание поездки и расчёт её стоимости.

```
app/main.py (консольное меню) → TaxiService → Repositories → SQLAlchemy 2.x → PostgreSQL
```

## Запуск
```bash
pip install -r requirements.txt
docker compose up -d            # PostgreSQL (или свой сервер; строка в .env, см. .env.example)
cp .env.example .env
python -m app.main              # таблицы создаются автоматически, пустая БД заполняется тестовыми данными
python -m pytest -v             # 12 тестов (SQLite в памяти)
```
Без PostgreSQL: `DATABASE_URL=sqlite:///taxi.db python -m app.main`.

## Модель данных
```
clients 1───N trips N───1 drivers N───M cars   (driver_cars — промежуточная таблица)
                trips N───1 cars
```
| Таблица | Ограничения |
|---|---|
| clients | PK, `phone` UNIQUE, NOT NULL |
| drivers | PK, `phone`, `license_number` UNIQUE, CHECK rating 1..5, CHECK experience ≥ 0 |
| cars | PK, `plate` UNIQUE |
| trips | PK, FK client (RESTRICT), FK driver/car (SET NULL), CHECK distance > 0, duration > 0, cost ≥ 0 |
| driver_cars | составной PK, 2 FK (CASCADE) |

Связи: one-to-many (`Client.trips`, `Driver.trips`), many-to-many (`Driver.cars` ↔ `Car.drivers`).

## Функциональность
* CRUD клиентов; получение по id, список с пагинацией (`page`, `page_size`).
* Поиск клиентов по части ФИО (`ilike`); фильтр поездок по нескольким условиям (статус + мин. стоимость + класс + дата);
  сортировки: водители по рейтингу/стажу/имени, поездки по дате/стоимости/расстоянию.
* Связанные данные: поездки клиента, машины водителей (`selectinload` — без проблемы N+1).
* **Транзакции** (`TaxiService.transaction()` — commit/rollback):
  * `create_trip`: проверка клиента → создание поездки → поиск свободного водителя с машиной нужного класса →
    назначение и смена статуса водителя. Нет водителя → rollback, поездка не сохраняется (тест).
  * `complete_trip`: пересчёт стоимости по факту, освобождение водителя, пересчёт рейтинга.
* Расчёт стоимости: подача + ₽/км + ₽/мин по классу (эконом 99/14/6, комфорт 149/19/8, бизнес 299/32/12), ночью ×1.25.
* Агрегаты: COUNT, SUM, AVG, MIN, MAX и GROUP BY по классам.
* Ошибки: `NotFoundError`, `DuplicateError` (UNIQUE), `ValidationError` (FK/CHECK/ввод), `BusinessRuleError`.

Доп. задания: B (пагинация), C (агрегаты), D (many-to-many), F (docker-compose), G (pytest).
