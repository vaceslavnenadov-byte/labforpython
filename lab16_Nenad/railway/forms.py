from django import forms
from django.utils import timezone

from .models import Passenger, Ticket, Train


class TrainForm(forms.ModelForm):
    class Meta:
        model = Train
        fields = ["number", "name", "route", "train_type", "departure", "seats_total", "base_price", "status"]
        widgets = {"departure": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")}

    def clean_number(self):
        number = self.cleaned_data["number"].strip().upper()
        if not number[:3].isdigit():
            raise forms.ValidationError("Номер поезда начинается с трёх цифр, например 001А")
        return number

    def clean(self):
        data = super().clean()
        departure = data.get("departure")
        if departure and not self.instance.pk and departure < timezone.now():
            self.add_error("departure", "Нельзя создать поезд с отправлением в прошлом")
        seats = data.get("seats_total")
        if seats and self.instance.pk and seats < self.instance.sold_count:
            self.add_error("seats_total", "Мест не может быть меньше, чем уже продано билетов")
        return data


class TicketPurchaseForm(forms.Form):
    """Обычная Django Form (не ModelForm): данные пассажира + номер места."""
    full_name = forms.CharField(label="ФИО пассажира", max_length=150)
    passport = forms.CharField(label="Паспорт", max_length=20)
    seat = forms.IntegerField(label="Место", min_value=1)

    def __init__(self, *args, train: Train, **kwargs):
        super().__init__(*args, **kwargs)
        self.train = train

    def clean_seat(self):
        seat = self.cleaned_data["seat"]
        if seat > self.train.seats_total:
            raise forms.ValidationError(f"Места пронумерованы от 1 до {self.train.seats_total}")
        if self.train.tickets.filter(seat=seat, status=Ticket.Status.PAID).exists():
            raise forms.ValidationError("Это место уже занято")
        return seat

    def clean(self):
        data = super().clean()
        if self.train.status in (Train.Status.DEPARTED, Train.Status.CANCELLED):
            raise forms.ValidationError("Продажа билетов на этот поезд закрыта")
        return data

    def save(self, user) -> Ticket:
        passenger, _ = Passenger.objects.get_or_create(
            passport=self.cleaned_data["passport"], defaults={"full_name": self.cleaned_data["full_name"]})
        return Ticket.objects.create(train=self.train, passenger=passenger, seat=self.cleaned_data["seat"],
                                     price=self.train.base_price)
