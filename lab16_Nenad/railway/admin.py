from django.contrib import admin

from .models import Passenger, Route, RouteStop, Station, Ticket, Train


class RouteStopInline(admin.TabularInline):
    model = RouteStop
    extra = 1
    autocomplete_fields = ["station"]


class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 0
    fields = ("passenger", "seat", "price", "status")
    autocomplete_fields = ["passenger"]


@admin.register(Train)
class TrainAdmin(admin.ModelAdmin):
    """Расширенная настройка: колонки, поиск, фильтры, сортировка, инлайны, действие."""
    list_display = ("number", "name", "route", "train_type", "departure", "seats_total", "free_seats", "base_price", "status")
    list_display_links = ("number", "name")
    list_editable = ("status",)
    search_fields = ("number", "name", "route__name")
    list_filter = ("status", "train_type", "route")
    ordering = ("departure",)
    date_hierarchy = "departure"
    list_select_related = ("route",)
    inlines = [TicketInline]
    actions = ["mark_cancelled"]

    @admin.action(description="Отменить выбранные поезда")
    def mark_cancelled(self, request, queryset):
        updated = queryset.update(status=Train.Status.CANCELLED)
        self.message_user(request, f"Отменено поездов: {updated}")


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    inlines = [RouteStopInline]


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ("name", "city")
    search_fields = ("name", "city")
    list_filter = ("city",)


@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "passport", "birth_date", "user")
    search_fields = ("full_name", "passport")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "train", "passenger", "seat", "price", "status", "purchased_at")
    list_filter = ("status", "train")
    search_fields = ("passenger__full_name", "train__number")
    list_select_related = ("train", "passenger")
