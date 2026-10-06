#!/bin/bash
# Локальный запуск без Docker: SQLite для каждого сервиса и Redis Streams как брокер (нужен redis-server).
export BROKER_URL=${BROKER_URL:-redis://localhost:6379/0} PYTHONPATH=.
DATABASE_URL=sqlite:///passengers.db uvicorn passenger_service.main:app --port 8001 &
DATABASE_URL=sqlite:///drivers.db uvicorn driver_service.main:app --port 8002 &
DATABASE_URL=sqlite:///orders.db uvicorn order_service.main:app --port 8003 &
DATABASE_URL=sqlite:///notifications.db uvicorn notification_service.main:app --port 8004 &
uvicorn gateway.main:app --port 8000 &
trap "kill 0" EXIT
wait
