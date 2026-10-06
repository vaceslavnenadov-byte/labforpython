"""Модели железнодорожной системы: станция, маршрут (M2M через RouteStop), поезд, пассажир, билет."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse


class Station(models.Model):
    name = models.CharField("Название", max_length=100, unique=True)
    city = models.CharField("Город", max_length=100)

    class Meta:
        ordering = ["name"]
        verbose_name = "станция"
        verbose_name_plural = "станции"

    def __str__(self):
        return self.name


class Route(models.Model):
    name = models.CharField("Маршрут", max_length=150, unique=True)
    stations = models.ManyToManyField(Station, through="RouteStop", related_name="routes", verbose_name="Станции")

    class Meta:
        ordering = ["name"]
        verbose_name = "маршрут"
        verbose_name_plural = "маршруты"

    def __str__(self):
        return self.name


class RouteStop(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="stops")
    station = models.ForeignKey(Station, on_delete=models.PROTECT)
    order = models.PositiveSmallIntegerField("Порядок")
    minutes_from_start = models.PositiveIntegerField("Минут от отправления", default=0)

    class Meta:
        ordering = ["route", "order"]
        constraints = [models.UniqueConstraint(fields=["route", "order"], name="unique_stop_order")]
        verbose_name = "остановка"
        verbose_name_plural = "остановки"

    def __str__(self):
        return f"{self.route}: {self.order}. {self.station}"


class Train(models.Model):
    class TrainType(models.TextChoices):
        FAST = "fast", "Скорый"
        PASSENGER = "passenger", "Пассажирский"
        HIGH_SPEED = "high_speed", "Высокоскоростной"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "По расписанию"
        DELAYED = "delayed", "Задерживается"
        DEPARTED = "departed", "Отправлен"
        CANCELLED = "cancelled", "Отменён"

    number = models.CharField("Номер", max_length=10, unique=True)
    name = models.CharField("Название", max_length=100, blank=True)
    route = models.ForeignKey(Route, on_delete=models.PROTECT, related_name="trains", verbose_name="Маршрут")
    train_type = models.CharField("Тип", max_length=12, choices=TrainType.choices, default=TrainType.FAST)
    departure = models.DateTimeField("Отправление")
    seats_total = models.PositiveIntegerField("Мест", validators=[MinValueValidator(1)])
    base_price = models.DecimalField("Цена", max_digits=9, decimal_places=2, validators=[MinValueValidator(1)])
    status = models.CharField("Статус", max_length=10, choices=Status.choices, default=Status.SCHEDULED)

    class Meta:
        ordering = ["departure"]
        verbose_name = "поезд"
        verbose_name_plural = "поезда"

    def __str__(self):
        return f"{self.number} {self.name}".strip()

    def get_absolute_url(self):
        return reverse("railway:train_detail", args=[self.pk])

    @property
    def sold_count(self) -> int:
        return self.tickets.filter(status=Ticket.Status.PAID).count()

    @property
    def free_seats(self) -> int:
        return self.seats_total - self.sold_count


class Passenger(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="passenger")
    full_name = models.CharField("ФИО", max_length=150)
    passport = models.CharField("Паспорт", max_length=20, unique=True)
    birth_date = models.DateField("Дата рождения", null=True, blank=True)

    class Meta:
        ordering = ["full_name"]
        verbose_name = "пассажир"
        verbose_name_plural = "пассажиры"

    def __str__(self):
        return self.full_name


class Ticket(models.Model):
    class Status(models.TextChoices):
        PAID = "paid", "Оплачен"
        RETURNED = "returned", "Возвращён"

    train = models.ForeignKey(Train, on_delete=models.CASCADE, related_name="tickets", verbose_name="Поезд")
    passenger = models.ForeignKey(Passenger, on_delete=models.PROTECT, related_name="tickets", verbose_name="Пассажир")
    seat = models.PositiveIntegerField("Место", validators=[MinValueValidator(1)])
    price = models.DecimalField("Цена", max_digits=9, decimal_places=2)
    status = models.CharField("Статус", max_length=10, choices=Status.choices, default=Status.PAID)
    purchased_at = models.DateTimeField("Куплен", auto_now_add=True)

    class Meta:
        ordering = ["-purchased_at"]
        constraints = [
            # одно место в поезде — один действующий билет
            models.UniqueConstraint(fields=["train", "seat"], condition=Q(status="paid"), name="unique_active_seat"),
        ]
        verbose_name = "билет"
        verbose_name_plural = "билеты"

    def __str__(self):
        return f"Билет №{self.pk}: {self.train.number}, место {self.seat}"

    def clean(self):
        if self.train_id and self.seat and self.seat > self.train.seats_total:
            raise ValidationError({"seat": f"В поезде только {self.train.seats_total} мест"})
