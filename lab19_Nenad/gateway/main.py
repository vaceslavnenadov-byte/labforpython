"""API Gateway — единая точка входа: маршрутизация, request id, журналирование, сводный health check."""

import os

from fastapi import FastAPI, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from common.observability import setup
from common.resilience import CircuitOpenError, ServiceClient, ServiceUnavailableError

SERVICE = "gateway"
ROUTES = {
    "passengers": ("passenger-service", "PASSENGER_SERVICE_URL", "http://localhost:8001"),
    "drivers": ("driver-service", "DRIVER_SERVICE_URL", "http://localhost:8002"),
    "orders": ("order-service", "ORDER_SERVICE_URL", "http://localhost:8003"),
    "notifications": ("notification-service", "NOTIFICATION_SERVICE_URL", "http://localhost:8004"),
}


def create_app(clients: dict[str, ServiceClient] | None = None) -> FastAPI:
    app = FastAPI(title="Taxi API Gateway", description="ЛР №19, вариант 10. Такси — микросервисы.")
    logger = setup(app, SERVICE)
    clients = clients or {prefix: ServiceClient(name, os.getenv(env, default), timeout=5.0, attempts=2,
                                                       fail_on_5xx=False)
                          for prefix, (name, env, default) in ROUTES.items()}

    @app.get("/status")
    def system_status():
        """Состояние всех сервисов (через их /health)."""
        result = {}
        for prefix, client in clients.items():
            try:
                ok = client.request("GET", "/health").status_code == 200
                result[client.name] = "✓ healthy" if ok else "✗ unhealthy"
            except ServiceUnavailableError as error:
                result[client.name] = f"✗ {error}"
        return result

    @app.api_route("/api/{resource}{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def proxy(resource: str, path: str, request: Request):
        client = clients.get(resource)
        if client is None:
            return JSONResponse({"detail": f"Unknown resource {resource}"}, status_code=404)
        body = await request.body()
        headers = {"Content-Type": request.headers.get("content-type", "application/json"),
                   "X-Request-ID": request.state.request_id}
        try:
            # синхронный HTTP-клиент выполняется в пуле потоков, чтобы не блокировать event loop
            upstream = await run_in_threadpool(client.request, request.method, f"/{resource}{path}",
                                               params=dict(request.query_params), content=body, headers=headers)
        except CircuitOpenError as error:
            return JSONResponse({"detail": str(error)}, status_code=503)
        except ServiceUnavailableError as error:
            logger.error("upstream %s unavailable: %s", client.name, error)
            return JSONResponse({"detail": str(error)}, status_code=503)
        return Response(upstream.content, status_code=upstream.status_code,
                        media_type=upstream.headers.get("content-type"))

    app.state.clients = clients
    return app


app = create_app() if os.getenv("SERVICE_AUTOSTART", "1") == "1" else None
