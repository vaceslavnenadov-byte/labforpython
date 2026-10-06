"""Представления: FBV (список, покупка, статистика) и CBV (Detail/Create/Update/Delete)."""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import TicketPurchaseForm, TrainForm
from .models import Passenger, Route, Station, Ticket, Train

logger = logging.getLogger("railway")
SORTS = {"departure": "departure", "-departure": "-departure", "price": "base_price",
         "-price": "-base_price", "number": "number", "free": "-free"}


def index(request):
    context = {
        "trains_count": Train.objects.count(),
        "stations_count": Station.objects.count(),
        "routes_count": Route.objects.count(),
        "tickets_count": Ticket.objects.filter(status=Ticket.Status.PAID).count(),
        "nearest": Train.objects.select_related("route").filter(status=Train.Status.SCHEDULED)[:5],
    }
    return render(request, "railway/index.html", context)


def train_list(request):
    """FBV: поиск, два фильтра, сортировка, пагинация — всё выполняется в БД."""
    trains = (Train.objects.select_related("route")          # без select_related был бы N+1 запросов к route
              .annotate(sold=Count("tickets", filter=Q(tickets__status=Ticket.Status.PAID)))
              .annotate(free=F("seats_total") - F("sold")))
    query = request.GET.get("q", "").strip()
    if query:
        trains = trains.filter(Q(number__icontains=query) | Q(name__icontains=query) |
                               Q(route__name__icontains=query) | Q(route__stations__city__icontains=query)).distinct()
    if request.GET.get("type"):
        trains = trains.filter(train_type=request.GET["type"])
    if request.GET.get("status"):
        trains = trains.filter(status=request.GET["status"])
    if request.GET.get("route"):
        trains = trains.filter(route_id=request.GET["route"])
    trains = trains.order_by(SORTS.get(request.GET.get("sort"), "departure"), "id")

    page = Paginator(trains, 10).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "railway/train_list.html", {
        "page_obj": page, "query": query, "params": params.urlencode(),
        "types": Train.TrainType.choices, "statuses": Train.Status.choices, "routes": Route.objects.all(),
    })


class TrainDetailView(DetailView):
    model = Train
    template_name = "railway/train_detail.html"

    def get_queryset(self):
        return Train.objects.select_related("route").prefetch_related("route__stops__station")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_staff:
            context["tickets"] = self.object.tickets.select_related("passenger")
        return context


class StaffRequiredMixin(PermissionRequiredMixin):
    """Создание/изменение/удаление — только администратор (is_staff + права модели)."""
    raise_exception = False

    def has_permission(self):
        return self.request.user.is_staff and super().has_permission()


class TrainCreateView(StaffRequiredMixin, CreateView):
    model = Train
    form_class = TrainForm
    template_name = "railway/train_form.html"
    permission_required = "railway.add_train"

    def form_valid(self, form):
        messages.success(self.request, "Поезд добавлен")
        logger.info("Создан поезд %s пользователем %s", form.instance.number, self.request.user)
        return super().form_valid(form)


class TrainUpdateView(StaffRequiredMixin, UpdateView):
    model = Train
    form_class = TrainForm
    template_name = "railway/train_form.html"
    permission_required = "railway.change_train"

    def form_valid(self, form):
        messages.success(self.request, "Изменения сохранены")
        return super().form_valid(form)


class TrainDeleteView(StaffRequiredMixin, DeleteView):
    model = Train
    template_name = "railway/train_confirm_delete.html"
    success_url = reverse_lazy("railway:train_list")
    permission_required = "railway.delete_train"

    def form_valid(self, form):
        messages.success(self.request, f"Поезд {self.object} удалён")
        return super().form_valid(form)


@login_required
def buy_ticket(request, pk: int):
    train = get_object_or_404(Train, pk=pk)
    form = TicketPurchaseForm(request.POST or None, train=train)
    if request.method == "POST" and form.is_valid():
        ticket = form.save(request.user)
        messages.success(request, f"Билет №{ticket.pk} оформлен: место {ticket.seat}")
        logger.info("Продан билет %s", ticket.pk)
        return redirect(train)
    busy = set(train.tickets.filter(status=Ticket.Status.PAID).values_list("seat", flat=True))
    return render(request, "railway/buy_ticket.html",
                  {"train": train, "form": form, "free": [s for s in range(1, train.seats_total + 1) if s not in busy][:40]})


class StationListView(ListView):
    """CBV-список станций с количеством маршрутов (annotate)."""
    model = Station
    template_name = "railway/station_list.html"
    paginate_by = 10

    def get_queryset(self):
        return Station.objects.annotate(routes_count=Count("routes", distinct=True)).order_by("city", "name")


def statistics(request):
    paid = Ticket.objects.filter(status=Ticket.Status.PAID)
    totals = paid.aggregate(revenue=Sum("price"), avg_price=Avg("price"))
    leader = (Route.objects.annotate(trains_count=Count("trains")).order_by("-trains_count").first())
    busiest = (Train.objects.annotate(sold=Count("tickets", filter=Q(tickets__status="paid")))
               .order_by("-sold").first())
    context = {
        "trains": Train.objects.count(),
        "active": Train.objects.exclude(status__in=["departed", "cancelled"]).count(),
        "tickets": paid.count(),
        "returned": Ticket.objects.filter(status=Ticket.Status.RETURNED).count(),
        "revenue": totals["revenue"] or 0,
        "avg_price": totals["avg_price"] or 0,
        "avg_train_price": Train.objects.aggregate(v=Avg("base_price"))["v"] or 0,
        "leader_route": leader,
        "busiest": busiest,
        "by_type": [{"label": Train.TrainType(row["train_type"]).label, "n": row["n"]}
                    for row in Train.objects.values("train_type").annotate(n=Count("id")).order_by("-n")],
        "passengers": Passenger.objects.count(),
    }
    return render(request, "railway/statistics.html", context)
