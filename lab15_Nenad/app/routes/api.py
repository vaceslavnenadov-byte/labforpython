"""REST API (JSON)."""

from flask import Blueprint, jsonify, request

from app.database import get_session
from app.exceptions import ValidationError
from app.models.models import CarClass, TripStatus
from app.services.services import TaxiService

api = Blueprint("api", __name__, url_prefix="/api")


def service() -> TaxiService:
    return TaxiService(get_session())


def body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Тело запроса должно быть JSON-объектом")
    return data


@api.get("/trips")
def list_trips():
    args = request.args
    try:
        trips, total = service().trips.search(
            text=args.get("q"), status=TripStatus(args["status"]) if args.get("status") else None,
            car_class=CarClass(args["car_class"]) if args.get("car_class") else None,
            sort=args.get("sort", "date"), order=args.get("order", "desc"),
            page=int(args.get("page", 1)), page_size=int(args.get("page_size", 20)))
    except ValueError:
        raise ValidationError("Некорректные параметры запроса") from None
    return jsonify({"items": [t.to_dict() for t in trips], "total": total})


@api.get("/trips/<int:trip_id>")
def get_trip(trip_id: int):
    return jsonify(service().get_trip(trip_id).to_dict())


@api.post("/trips")
def create_trip():
    return jsonify(service().create_trip(body()).to_dict()), 201


@api.put("/trips/<int:trip_id>")
def replace_trip(trip_id: int):
    return jsonify(service().update_trip(trip_id, body(), partial=False).to_dict())


@api.patch("/trips/<int:trip_id>")
def patch_trip(trip_id: int):
    return jsonify(service().update_trip(trip_id, body(), partial=True).to_dict())


@api.delete("/trips/<int:trip_id>")
def delete_trip(trip_id: int):
    service().delete_trip(trip_id)
    return "", 204


@api.get("/drivers")
def list_drivers():
    return jsonify([{"id": d.id, "full_name": d.full_name, "car": f"{d.car_model} {d.car_plate}",
                     "car_class": d.car_class.value, "rating": d.rating, "trips": len(d.trips)}
                    for d in service().drivers.all()])
