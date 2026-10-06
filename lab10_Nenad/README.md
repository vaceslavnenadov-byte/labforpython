# ЛР №10 — HTTP и REST API (Flask)

**Вариант 10. Железная дорога** — ресурс `Train`, специализированная операция: **свободные места**.

```
client.py ──HTTP/JSON──► Flask (routes.py) ──► TrainService ──► TrainRepository (память)
```

```bash
pip install -r requirements.txt
python app.py                 # сервер http://127.0.0.1:5000
python client.py              # консольный клиент (requests)
python -m pytest -v           # 17 тестов
```

Изменяющие запросы требуют заголовок `X-API-Key: secret-key` (переменная окружения `API_KEY`).

## API

| Метод | Endpoint | Назначение | Код |
|---|---|---|---|
| GET | /trains | список (фильтры `from`, `to`, `status`, `date`, `min_price`, `max_price`; сортировка `sort=price\|departure_time\|free_seats\|number&order=asc\|desc`; пагинация `page`, `limit`) | 200 |
| GET | /trains/{id} | поезд | 200 / 404 |
| POST | /trains | создание | 201 / 400 / 409 |
| PUT | /trains/{id} | полная замена | 200 / 400 / 404 |
| PATCH | /trains/{id} | частичное изменение | 200 / 400 / 404 |
| DELETE | /trains/{id} | удаление (только без проданных мест или отменённый) | 204 / 404 / 409 |
| GET | /trains/free-seats?min_seats=N | **поезда со свободными местами** | 200 |
| POST | /trains/{id}/bookings `{"count": 2}` | покупка мест | 201 / 409 |

Ошибки в едином формате: `{"error": "Train 999 not found", "code": "TRAIN_NOT_FOUND"}` (400, 401, 404, 405, 409, 500).

### Примеры

```http
POST /trains
X-API-Key: secret-key
Content-Type: application/json

{"number": "777М", "departure_station": "Москва", "arrival_station": "Тверь",
 "departure_time": "2026-10-20T08:00", "arrival_time": "2026-10-20T10:00",
 "wagons": 5, "seats_per_wagon": 60, "price": 900}

→ 201 Created, Location: /trains/7
```

```http
GET /trains/free-seats?min_seats=200
→ 200 [{"id": 3, "number": "104В", "route": "Москва - Казань", "free_seats": 254, ...}, ...]
```

Доп. задания: пагинация, проверка заголовка API-ключа (401), middleware логирования
`GET /trains -> 200 -> 0.3 ms`, заголовок `X-Response-Time-ms`.
