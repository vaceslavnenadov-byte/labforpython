"""Заказы: создание, просмотр, смена статуса, статистика, уведомления."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.app.api.deps import current_user, get_cache, get_db, require_admin
from src.app.cache import Cache
from src.app.models import OrderStatus, User
from src.app.schemas import NotificationOut, OrderIn, OrderList, OrderOut, QuoteIn, QuoteOut
from src.app.services.services import OrderService, notifications_for

router = APIRouter(tags=["orders"])


def service(db: Session = Depends(get_db), cache: Cache = Depends(get_cache)) -> OrderService:
    return OrderService(db, cache)


@router.post("/orders/quote", response_model=QuoteOut, dependencies=[Depends(current_user)])
def quote(data: QuoteIn, orders: OrderService = Depends(service)):
    """Предварительный расчёт стоимости с учётом текущего спроса."""
    return orders.quote(data.car_class, data.distance_km)


@router.post("/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(data: OrderIn, user: User = Depends(current_user), orders: OrderService = Depends(service)):
    return orders.create(user, data)


@router.get("/orders", response_model=OrderList)
def list_orders(status_: OrderStatus | None = Query(None, alias="status"),
                q: str | None = Query(None, min_length=2, description="поиск по адресу"),
                sort: str = Query("created_at", pattern="^(created_at|price|distance)$"),
                order: str = Query("desc", pattern="^(asc|desc)$"),
                skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
                user: User = Depends(current_user), orders: OrderService = Depends(service)):
    """Пассажир видит свои заказы, администратор — все."""
    items, total = orders.search(user, status_, q, sort, order, skip, limit)
    return OrderList(items=items, total=total, skip=skip, limit=limit)


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, user: User = Depends(current_user), orders: OrderService = Depends(service)):
    return orders.get(user, order_id)


@router.post("/orders/{order_id}/start", response_model=OrderOut)
def start(order_id: int, user: User = Depends(require_admin), orders: OrderService = Depends(service)):
    return orders.change_status(user, order_id, OrderStatus.IN_PROGRESS)


@router.post("/orders/{order_id}/complete", response_model=OrderOut)
def complete(order_id: int, user: User = Depends(require_admin), orders: OrderService = Depends(service)):
    return orders.change_status(user, order_id, OrderStatus.COMPLETED)


@router.post("/orders/{order_id}/cancel", response_model=OrderOut)
def cancel(order_id: int, user: User = Depends(current_user), orders: OrderService = Depends(service)):
    return orders.change_status(user, order_id, OrderStatus.CANCELLED)


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_order(order_id: int, orders: OrderService = Depends(service)):
    orders.delete(order_id)


@router.get("/stats", dependencies=[Depends(require_admin)])
def stats(orders: OrderService = Depends(service)):
    return orders.statistics()


@router.get("/notifications", response_model=list[NotificationOut])
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return notifications_for(db, user)
