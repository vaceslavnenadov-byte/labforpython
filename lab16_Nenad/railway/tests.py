from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import IntegrityError, connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from .models import Route, Ticket, Train


class RailwayTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_data", verbosity=0)
        cls.train = Train.objects.get(number="001А")
        cls.form_data = {"number": "999Т", "name": "Тестовый", "route": Route.objects.first().pk,
                         "train_type": "fast", "seats_total": 100, "base_price": "1500.00", "status": "scheduled",
                         "departure": (timezone.now() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")}

    def login_admin(self):
        self.client.login(username="admin", password="admin12345")

    def login_user(self):
        self.client.login(username="user", password="user12345")

    # 1–3. главная, список, детальная
    def test_index(self):
        response = self.client.get(reverse("railway:index"))
        self.assertContains(response, "24</b>поездов")

    def test_list(self):
        response = self.client.get(reverse("railway:train_list"))
        self.assertEqual(response.context["page_obj"].paginator.count, 24)

    def test_detail_shows_route(self):
        response = self.client.get(self.train.get_absolute_url())
        self.assertContains(response, "Бологое")

    # 4–6. создание, изменение, удаление
    def test_create(self):
        self.login_admin()
        response = self.client.post(reverse("railway:train_create"), self.form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Train.objects.filter(number="999Т").exists())

    def test_update(self):
        self.login_admin()
        data = {**self.form_data, "number": self.train.number, "base_price": "3333.00"}
        self.client.post(reverse("railway:train_edit", args=[self.train.pk]), data)
        self.train.refresh_from_db()
        self.assertEqual(str(self.train.base_price), "3333.00")

    def test_delete(self):
        self.login_admin()
        response = self.client.post(reverse("railway:train_delete", args=[self.train.pk]))
        self.assertRedirects(response, reverse("railway:train_list"))
        self.assertFalse(Train.objects.filter(pk=self.train.pk).exists())

    # 7–10. поиск, фильтрация, сортировка, пагинация
    def test_search_by_city(self):
        response = self.client.get(reverse("railway:train_list"), {"q": "Сочи"})
        numbers = {t.route.name for t in response.context["page_obj"]}
        self.assertEqual(numbers, {"Москва — Сочи"})

    def test_filters(self):
        response = self.client.get(reverse("railway:train_list"), {"type": "high_speed", "status": "scheduled"})
        trains = list(response.context["page_obj"])
        self.assertTrue(trains and all(t.train_type == "high_speed" and t.status == "scheduled" for t in trains))

    def test_sorting(self):
        response = self.client.get(reverse("railway:train_list"), {"sort": "-price"})
        prices = [t.base_price for t in response.context["page_obj"]]
        self.assertEqual(prices, sorted(prices, reverse=True))

    def test_pagination(self):
        response = self.client.get(reverse("railway:train_list"), {"page": 3})
        self.assertEqual(len(response.context["page_obj"]), 4)        # 24 = 10 + 10 + 4

    # 11. валидация
    def test_validation_errors(self):
        self.login_admin()
        bad = {**self.form_data, "number": "АБВ", "seats_total": 0,
               "departure": (timezone.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")}
        response = self.client.post(reverse("railway:train_create"), bad)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context["form"].errors), {"number", "seats_total", "departure"})

    # 12–14. авторизация и права
    def test_anonymous_cannot_buy(self):
        response = self.client.get(reverse("railway:buy_ticket", args=[self.train.pk]))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('railway:buy_ticket', args=[self.train.pk])}")

    def test_regular_user_cannot_create(self):
        self.login_user()
        response = self.client.post(reverse("railway:train_create"), self.form_data)
        self.assertIn(response.status_code, (302, 403))
        self.assertFalse(Train.objects.filter(number="999Т").exists())

    def test_admin_sees_tickets_user_does_not(self):
        self.login_user()
        self.assertNotIn("tickets", self.client.get(self.train.get_absolute_url()).context)
        self.login_admin()
        self.assertIn("tickets", self.client.get(self.train.get_absolute_url()).context)

    def test_user_buys_ticket_and_seat_becomes_busy(self):
        self.login_user()
        free_before = self.train.free_seats
        url = reverse("railway:buy_ticket", args=[self.train.pk])
        self.client.post(url, {"full_name": "Тест", "passport": "0000 1", "seat": 200})
        self.assertEqual(self.train.free_seats, free_before - 1)
        response = self.client.post(url, {"full_name": "Тест 2", "passport": "0000 2", "seat": 200})
        self.assertContains(response, "уже занято")

    # 15. связи моделей и ограничения
    def test_relations_and_constraint(self):
        route = self.train.route
        self.assertEqual(route.stations.count(), 4)                          # M2M через RouteStop
        self.assertIn(self.train, route.trains.all())                       # обратная связь FK
        ticket = Ticket.objects.filter(train=self.train, status="paid").first()
        with self.assertRaises(IntegrityError):
            Ticket.objects.create(train=self.train, passenger=ticket.passenger, seat=ticket.seat, price=1)

    def test_statistics_page(self):
        response = self.client.get(reverse("railway:statistics"))
        self.assertEqual(response.context["tickets"], 28)
        self.assertEqual(response.context["leader_route"].name, "Москва — Санкт-Петербург")

    def test_select_related_avoids_n_plus_one(self):
        with CaptureQueriesContext(connection) as bad:
            [t.route.name for t in Train.objects.all()]                      # N+1: 1 + 24 запроса
        with CaptureQueriesContext(connection) as good:
            [t.route.name for t in Train.objects.select_related("route")]    # 1 запрос с JOIN
        self.assertEqual(len(bad), 25)
        self.assertEqual(len(good), 1)

    def test_orm_queries(self):
        self.assertTrue(Train.objects.filter(number__startswith="75").exists())
        self.assertEqual(Train.objects.exclude(status="scheduled").count(), 2)
        self.assertEqual(Train.objects.get(number="026Ч").get_status_display(), "Задерживается")
