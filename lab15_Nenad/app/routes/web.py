"""HTML-интерфейс (Jinja2)."""

import logging
import secrets

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for

from app.database import get_session
from app.exceptions import AppError
from app.models.models import CarClass, TripStatus
from app.services.services import TaxiService

web = Blueprint("web", __name__)
logger = logging.getLogger("taxi.web")


def service() -> TaxiService:
    return TaxiService(get_session())


@web.app_context_processor
def inject_globals():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return {"csrf_token": session["csrf_token"], "CarClass": CarClass, "TripStatus": TripStatus}


@web.before_app_request
def check_csrf():
    """Простая защита HTML-форм от CSRF (доп. задание 29.3); JSON API её не требует."""
    if request.method == "POST" and request.blueprint == "web" and not current_app.config.get("WTF_CSRF_DISABLED"):
        token = request.form.get("csrf_token")
        if not token or token != session.get("csrf_token"):
            abort(400, description="Неверный CSRF-токен")


def _int_or_none(name):
    value = request.args.get(name, "")
    return int(value) if value.isdigit() else None


@web.get("/")
def index():
    svc = service()
    recent, _ = svc.trips.search(page_size=5)
    return render_template("index.html", summary=svc.trips.summary(), recent=recent)


@web.get("/trips")
def trip_list():
    svc = service()
    status = request.args.get("status") or None
    car_class = request.args.get("car_class") or None
    page = max(_int_or_none("page") or 1, 1)
    try:
        trips, total = svc.trips.search(
            text=request.args.get("q", "").strip() or None,
            status=TripStatus(status) if status else None,
            car_class=CarClass(car_class) if car_class else None,
            driver_id=_int_or_none("driver_id"),
            sort=request.args.get("sort", "date"), order=request.args.get("order", "desc"),
            page=page, page_size=current_app.config["PAGE_SIZE"])
    except ValueError:
        abort(400, description="Некорректный фильтр")
    pages = max((total + current_app.config["PAGE_SIZE"] - 1) // current_app.config["PAGE_SIZE"], 1)
    return render_template("list.html", trips=trips, total=total, page=page, pages=pages,
                           drivers=svc.drivers.all(), args=request.args,
                           base_args={k: v for k, v in request.args.items() if k != "page"})


@web.get("/trips/<int:trip_id>")
def trip_detail(trip_id: int):
    return render_template("detail.html", trip=service().get_trip(trip_id))


@web.route("/trips/create", methods=["GET", "POST"])
def trip_create():
    svc = service()
    if request.method == "POST":
        try:
            trip = svc.create_trip({k: request.form.get(k) for k in
                                    ("client_id", "driver_id", "pickup", "destination", "distance_km", "duration_min")})
            logger.info("Создана поездка %s", trip.id)
            flash(f"Поездка №{trip.id} создана, стоимость {trip.cost:.2f} ₽", "success")
            return redirect(url_for("web.trip_detail", trip_id=trip.id))
        except AppError as error:
            flash(error.message, "error")
    return render_template("create.html", drivers=svc.drivers.all(), clients=svc.clients.all(),
                           form=request.form if request.method == "POST" else request.args)


@web.route("/trips/<int:trip_id>/edit", methods=["GET", "POST"])
def trip_edit(trip_id: int):
    svc = service()
    trip = svc.get_trip(trip_id)
    if request.method == "POST":
        try:
            svc.update_trip(trip_id, {k: request.form.get(k) for k in
                                      ("driver_id", "pickup", "destination", "distance_km", "duration_min", "status")})
            logger.info("Изменена поездка %s", trip_id)
            flash("Изменения сохранены", "success")
            return redirect(url_for("web.trip_detail", trip_id=trip_id))
        except AppError as error:
            flash(error.message, "error")
    return render_template("edit.html", trip=trip, drivers=svc.drivers.all())


@web.post("/trips/<int:trip_id>/delete")
def trip_delete(trip_id: int):
    try:
        service().delete_trip(trip_id)
        logger.warning("Удалена поездка %s", trip_id)
        flash(f"Поездка №{trip_id} удалена", "success")
    except AppError as error:
        flash(error.message, "error")
        return redirect(url_for("web.trip_detail", trip_id=trip_id))
    return redirect(url_for("web.trip_list"))


@web.route("/drivers", methods=["GET", "POST"])
def drivers():
    svc = service()
    if request.method == "POST":
        try:
            driver = svc.create_driver(request.form)
            flash(f"Водитель {driver.full_name} добавлен", "success")
            return redirect(url_for("web.drivers"))
        except AppError as error:
            flash(error.message, "error")
    return render_template("drivers.html", drivers=svc.drivers.all())


@web.get("/drivers/<int:driver_id>")
def driver_detail(driver_id: int):
    driver = service().drivers.get(driver_id)
    if driver is None:
        abort(404)
    return render_template("driver_detail.html", driver=driver)


@web.route("/clients", methods=["GET", "POST"])
def clients():
    svc = service()
    if request.method == "POST":
        try:
            client = svc.create_client(request.form)
            flash(f"Клиент {client.full_name} добавлен", "success")
            return redirect(url_for("web.clients"))
        except AppError as error:
            flash(error.message, "error")
    return render_template("clients.html", clients=svc.clients.all())


@web.get("/clients/<int:client_id>")
def client_detail(client_id: int):
    client = service().clients.get(client_id)
    if client is None:
        abort(404)
    return render_template("client_detail.html", client=client)
