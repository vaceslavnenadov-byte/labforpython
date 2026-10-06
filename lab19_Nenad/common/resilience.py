"""Паттерны отказоустойчивости: Retry (с exponential backoff) и Circuit Breaker, HTTP-клиент сервиса."""

import logging
import threading
import time
from enum import Enum
from typing import Callable, TypeVar

import httpx

logger = logging.getLogger("resilience")
T = TypeVar("T")


class ServiceUnavailableError(Exception):
    """Зависимый сервис недоступен (после повторов или при открытом предохранителе)."""


class CircuitOpenError(ServiceUnavailableError):
    pass


class BreakerState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """CLOSED → (failure_threshold ошибок подряд) → OPEN → (recovery_timeout) → HALF_OPEN → успех: CLOSED / ошибка: OPEN."""

    def __init__(self, name: str, failure_threshold: int = 3, recovery_timeout: float = 10.0,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.clock = clock
        self.failures = 0
        self.opened_at = 0.0
        self._state = BreakerState.CLOSED
        self._lock = threading.Lock()

    @property
    def state(self) -> BreakerState:
        with self._lock:
            if self._state == BreakerState.OPEN and self.clock() - self.opened_at >= self.recovery_timeout:
                self._state = BreakerState.HALF_OPEN
                logger.info("circuit %s -> HALF_OPEN (пробный запрос)", self.name)
            return self._state

    def call(self, func: Callable[[], T]) -> T:
        if self.state == BreakerState.OPEN:
            raise CircuitOpenError(f"Сервис {self.name} временно недоступен (circuit breaker OPEN)")
        try:
            result = func()
        except Exception:
            self._on_failure()
            raise
        self._on_success()
        return result

    def _on_success(self) -> None:
        with self._lock:
            if self._state != BreakerState.CLOSED:
                logger.info("circuit %s -> CLOSED", self.name)
            self._state = BreakerState.CLOSED
            self.failures = 0

    def _on_failure(self) -> None:
        with self._lock:
            self.failures += 1
            if self._state == BreakerState.HALF_OPEN or self.failures >= self.failure_threshold:
                self._state = BreakerState.OPEN
                self.opened_at = self.clock()
                logger.warning("circuit %s -> OPEN после %d ошибок", self.name, self.failures)


class RetryableError(Exception):
    """Временная ошибка (5xx), запрос имеет смысл повторить."""


def retry(func: Callable[[], T], attempts: int = 3, base_delay: float = 0.2,
          retry_on: tuple[type[Exception], ...] = (httpx.TransportError, RetryableError),
          sleep: Callable[[float], None] = time.sleep) -> T:
    """Повтор с экспоненциальной задержкой: 0.2 с, 0.4 с, 0.8 с … Число попыток ограничено."""
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except retry_on as error:
            if attempt == attempts:
                raise
            delay = base_delay * 2 ** (attempt - 1)
            logger.warning("попытка %d/%d не удалась (%s), повтор через %.1f с", attempt, attempts, error, delay)
            sleep(delay)
    raise AssertionError("unreachable")


class ServiceClient:
    """HTTP-клиент к другому сервису: тайм-аут + Retry + Circuit Breaker."""

    def __init__(self, name: str, base_url: str, timeout: float = 2.0, attempts: int = 3,
                 breaker: CircuitBreaker | None = None, transport: httpx.BaseTransport | None = None,
                 sleep: Callable[[float], None] = time.sleep, fail_on_5xx: bool = True) -> None:
        self.name = name
        self.http = httpx.Client(base_url=base_url, timeout=timeout, transport=transport)
        self.attempts = attempts
        self.breaker = breaker or CircuitBreaker(name)
        self.sleep = sleep
        # False — ответ 5xx считается обычным ответом (нужно шлюзу: 503 от сервиса означает, что упала его
        # зависимость, а сам сервис работает; открывать предохранитель на него нельзя)
        self.fail_on_5xx = fail_on_5xx

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        def once() -> httpx.Response:
            response = self.http.request(method, url, **kwargs)
            if self.fail_on_5xx and response.status_code >= 500:
                raise RetryableError(f"{self.name} ответил {response.status_code}")
            return response

        try:
            return self.breaker.call(lambda: retry(once, self.attempts, sleep=self.sleep))
        except CircuitOpenError:
            raise
        except (httpx.TransportError, RetryableError) as error:
            raise ServiceUnavailableError(f"Сервис {self.name} недоступен: {error}") from error
