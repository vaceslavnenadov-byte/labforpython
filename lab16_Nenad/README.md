# ЛР №16 — Веб-приложение на Django

**Вариант 10. Железнодорожная система**: модели `Train`, `Station`, `Route` (+ `RouteStop`), `Passenger`, `Ticket`;
поезда, маршруты, станции, расписание, билеты.

## Запуск
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data          # 24 поезда, 12 станций, 5 маршрутов, 10 пассажиров, 30 билетов, 2 пользователя
python manage.py runserver          # http://127.0.0.1:8000/   админка: http://127.0.0.1:8000/admin/
python manage.py test railway       # 19 тестов
```
Пользователи: `admin / admin12345` (администратор, superuser), `user / user12345` (обычный пользователь).
Свой администратор: `python manage.py createsuperuser`.
PostgreSQL: задать `DB_ENGINE=postgres` и `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` (см. `.env.example`).

## Структура
```
config/          settings.py, urls.py, wsgi.py, asgi.py
railway/         models.py, forms.py, views.py, urls.py, admin.py, middleware.py, tests.py,
                 management/commands/seed_data.py, templates/railway/*.html
templates/       base.html, registration/login.html
```

## Модели и связи (ER)
```
Station N───M Route   (через RouteStop: порядок, минуты в пути)
Route   1───N Train
Train   1───N Ticket N───1 Passenger 1───1 User (необязательная)
```
Ограничения: `unique` номера поезда/станции/паспорта, `UniqueConstraint(train, seat) WHERE status='paid'` —
одно место = один действующий билет; `MinValueValidator` для мест и цены.

## Функциональность
| URL | Что делает | Как реализовано |
|---|---|---|
| `/` | название, описание, количество объектов, ближайшие поезда, текущий пользователь | FBV |
| `/trains/` | список: поиск `q` (номер, название, маршрут, город станции), фильтры `type`, `status`, `route`, сортировка `sort` (отправление ↑↓, цена ↑↓, свободные места, номер), пагинация по 10 | FBV, `select_related` + `annotate` |
| `/trains/<id>/` | карточка: маршрут со станциями, свободные места; администратору — проданные билеты | `DetailView` + `prefetch_related` |
| `/trains/create/`, `/<id>/edit/`, `/<id>/delete/` | CRUD (только администратор), подтверждение удаления | `CreateView`, `UpdateView`, `DeleteView` + `ModelForm` |
| `/trains/<id>/buy/` | покупка билета (нужен вход) | FBV + `forms.Form` с валидацией места |
| `/stations/` | станции с количеством маршрутов | `ListView` + `annotate` |
| `/statistics/` | 8 показателей: поезда, в продаже, билеты, возвраты, выручка, средние цены, маршрут-лидер, загруженный поезд, по типам | `aggregate`, `annotate` |
| `/admin/` | Django Admin: list_display, search_fields, list_filter, ordering, date_hierarchy, list_editable, инлайны, действие «Отменить» | `admin.py` |

ORM: `all()`, `filter()`, `exclude()`, `get()`, `order_by()`, `count()`, `exists()`, `aggregate()`, `annotate()`,
`select_related()`, `prefetch_related()`, связанные объекты (`route.trains`, `route.stations`, `train.tickets`).

**N+1:** `[t.route.name for t in Train.objects.all()]` делает 1 + 24 запроса; с `select_related("route")` — 1 запрос с JOIN
(проверено тестом `test_select_related_avoids_n_plus_one`).

Доступ: гость — просмотр, поиск, фильтрация; пользователь — ещё покупка билетов; администратор — создание, изменение,
удаление, просмотр билетов, админка. Безопасность: CSRF-токены во всех формах, хеширование паролей Django,
экранирование в шаблонах, `PermissionRequiredMixin`, `login_required`. Middleware `RequestTimingMiddleware`
журналирует каждый запрос.

## Сравнение Django, Flask и FastAPI
| Возможность | Django | Flask | FastAPI |
|---|---|---|---|
| ORM | встроенная | нет (SQLAlchemy) | нет (SQLAlchemy) |
| Шаблоны | встроены | Jinja2 | не основной сценарий |
| Admin | встроен | нет | нет |
| Формы | встроены | расширения | Pydantic |
| REST API | через DRF | удобно | основной сценарий |
| OpenAPI | через DRF | расширения | встроено |
| Аутентификация | встроенная | расширения | вручную |

Вывод: Django выгоден для полноценных веб-систем с пользователями, правами и админкой (как эта система продажи билетов);
Flask — для небольших сервисов, где нужна свобода выбора компонентов; FastAPI — для API, микросервисов и асинхронной работы.
