"""HTTP-слой: только разбор запроса и формирование ответа. Логика — в TrainService."""

from flask import Blueprint, current_app, jsonify, request

from exceptions import ValidationError

api = Blueprint("api", __name__)


def service():
    return current_app.config["TRAIN_SERVICE"]


def _float_arg(name: str):
    value = request.args.get(name)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        raise ValidationError(f"Query parameter '{name}' must be a number") from None


def _int_arg(name: str, default: int) -> int:
    value = request.args.get(name, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"Query parameter '{name}' must be an integer") from None


def _filters() -> dict:
    return {
        "from": request.args.get("from"),
        "to": request.args.get("to"),
        "status": request.args.get("status"),
        "date": request.args.get("date"),
        "min_price": _float_arg("min_price"),
        "max_price": _float_arg("max_price"),
    }


def _json_body() -> dict:
    data = request.get_json(silent=True)
    if data is None:
        raise ValidationError("Request body must be valid JSON with Content-Type: application/json")
    return data


@api.get("/trains")
def list_trains():
    trains = service().get_trains(_filters(), request.args.get("sort"), request.args.get("order", "asc"))
    items = [t.to_dict() for t in trains]
    if "page" in request.args or "limit" in request.args:   # пагинация (доп. задание 1)
        page, limit = _int_arg("page", 1), _int_arg("limit", 10)
        if page < 1 or not 1 <= limit <= 100:
            raise ValidationError("page must be >= 1, limit must be in 1..100")
        start = (page - 1) * limit
        return jsonify({"items": items[start:start + limit], "page": page, "limit": limit, "total": len(items)})
    return jsonify(items)


@api.get("/trains/free-seats")
def free_seats():
    """Специализированная операция варианта 10: поезда со свободными местами."""
    return jsonify(service().trains_with_free_seats(_int_arg("min_seats", 1), _filters()))


@api.get("/trains/<int:train_id>")
def get_train(train_id: int):
    return jsonify(service().get_train(train_id).to_dict())


@api.post("/trains")
def create_train():
    train = service().create_train(_json_body())
    response = jsonify(train.to_dict())
    response.status_code = 201
    response.headers["Location"] = f"/trains/{train.id}"
    return response


@api.put("/trains/<int:train_id>")
def replace_train(train_id: int):
    return jsonify(service().replace_train(train_id, _json_body()).to_dict())


@api.patch("/trains/<int:train_id>")
def patch_train(train_id: int):
    return jsonify(service().patch_train(train_id, _json_body()).to_dict())


@api.delete("/trains/<int:train_id>")
def delete_train(train_id: int):
    service().delete_train(train_id)
    return "", 204


@api.post("/trains/<int:train_id>/bookings")
def book_seats(train_id: int):
    body = _json_body()
    count = body.get("count")
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValidationError("Field 'count' must be an integer")
    return jsonify(service().book_seats(train_id, count).to_dict()), 201
