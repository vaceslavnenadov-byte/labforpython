import logging
import time

logger = logging.getLogger("railway")


class RequestTimingMiddleware:
    """Журналирует метод, путь, код ответа и время обработки запроса."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        logger.info("%s %s -> %s (%.1f ms)", request.method, request.path, response.status_code,
                    (time.perf_counter() - start) * 1000)
        return response
