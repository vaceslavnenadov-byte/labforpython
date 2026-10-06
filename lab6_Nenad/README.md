# ЛР №6 — Декораторы, контекстные менеджеры, dataclass, Enum, Protocol, интроспекция

**Вариант 10. Железнодорожные перевозки** — поезда, вагоны, билеты.

Запуск: `python main.py`

| Файл | Содержимое |
|---|---|
| `models.py` | dataclass `Entity` → `Train`, `Wagon`, `Ticket`; Enum `WagonType`, `TicketStatus` |
| `decorators.py` | `@log_call`, `@timing`, `@require_status(...)`, `@retry(n)`, `@command(...)` |
| `context.py` | `Transaction` (откат при ошибке), `OperationLogger` (журнал в файл), `measure` (`@contextmanager`) |
| `protocols.py` | Protocol `Reportable` и функция `print_report` |
| `introspection.py` | `inspect_object` (type, isinstance, issubclass, dir, hasattr, getattr, inspect.signature, inspect.getmembers), `safe_set` (setattr) |
| `services.py` | `RailwayService`: CRUD, бронирование, оплата, возврат, загрузка поезда, свободные места, статистика |
| `exceptions.py` | `EntityNotFoundError`, `SeatUnavailableError`, `InvalidStatusError`, `ValidationError` |
| `main.py` | `ConsoleUI` — меню строится автоматически по методам с `@command` |

Статусы билета: забронирован → оплачен → использован; забронирован/оплачен → возвращён.
