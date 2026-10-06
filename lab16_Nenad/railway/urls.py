from django.urls import path

from . import views

app_name = "railway"

urlpatterns = [
    path("", views.index, name="index"),
    path("trains/", views.train_list, name="train_list"),
    path("trains/create/", views.TrainCreateView.as_view(), name="train_create"),
    path("trains/<int:pk>/", views.TrainDetailView.as_view(), name="train_detail"),
    path("trains/<int:pk>/edit/", views.TrainUpdateView.as_view(), name="train_edit"),
    path("trains/<int:pk>/delete/", views.TrainDeleteView.as_view(), name="train_delete"),
    path("trains/<int:pk>/buy/", views.buy_ticket, name="buy_ticket"),
    path("stations/", views.StationListView.as_view(), name="station_list"),
    path("statistics/", views.statistics, name="statistics"),
]
