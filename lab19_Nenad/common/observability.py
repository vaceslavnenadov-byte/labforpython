"""Логирование с именем сервиса и request id, health check."""

import logging
import time
import uuid

from fastapi import FastAPI, Request


def setup(app: FastAPI, service_name: str) -> logging.Logger:
    logging.basicConfig(level=logging.INFO,
                        format=f"%(asctime)s {service_name} %(levelname)s %(message)s")
    logger = logging.getLogger(service_name)

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_id=%s %s %s failed", request_id, request.method, request.url.path)
            raise
        response.headers["X-Request-ID"] = request_id
        logger.info("request_id=%s %s %s status=%s duration=%.0fms", request_id, request.method,
                    request.url.path, response.status_code, (time.perf_counter() - start) * 1000)
        return response

    @app.get("/health", tags=["service"])
    def health():
        return {"status": "healthy", "service": service_name}

    return logger
