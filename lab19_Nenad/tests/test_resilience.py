import httpx
import pytest

from common.resilience import (BreakerState, CircuitBreaker, CircuitOpenError, RetryableError, ServiceClient,
                               ServiceUnavailableError, retry)


def test_retry_succeeds_after_temporary_errors():
    calls, delays = [], []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise RetryableError("503")
        return "ok"

    assert retry(flaky, attempts=3, base_delay=0.1, sleep=delays.append) == "ok"
    assert delays == [0.1, 0.2]                       # exponential backoff


def test_retry_gives_up_after_limit():
    with pytest.raises(RetryableError):
        retry(lambda: (_ for _ in ()).throw(RetryableError("down")), attempts=2, sleep=lambda s: None)


def test_circuit_breaker_states():
    now = [0.0]
    breaker = CircuitBreaker("svc", failure_threshold=2, recovery_timeout=10, clock=lambda: now[0])

    def fail():
        raise ConnectionError

    for _ in range(2):
        with pytest.raises(ConnectionError):
            breaker.call(fail)
    assert breaker.state == BreakerState.OPEN
    with pytest.raises(CircuitOpenError):              # запрос даже не выполняется
        breaker.call(lambda: "never")
    now[0] = 11
    assert breaker.state == BreakerState.HALF_OPEN
    assert breaker.call(lambda: "ok") == "ok"
    assert breaker.state == BreakerState.CLOSED


def test_half_open_failure_reopens():
    now = [0.0]
    breaker = CircuitBreaker("svc", failure_threshold=1, recovery_timeout=5, clock=lambda: now[0])
    with pytest.raises(ZeroDivisionError):
        breaker.call(lambda: 1 / 0)
    now[0] = 6
    with pytest.raises(ZeroDivisionError):
        breaker.call(lambda: 1 / 0)
    assert breaker.state == BreakerState.OPEN


def test_service_client_retries_5xx_then_success():
    responses = iter([httpx.Response(503), httpx.Response(200, json={"ok": True})])
    client = ServiceClient("svc", "http://svc", transport=httpx.MockTransport(lambda r: next(responses)),
                           sleep=lambda s: None)
    assert client.request("GET", "/x").json() == {"ok": True}


def test_service_client_unavailable():
    client = ServiceClient("svc", "http://svc", attempts=2, sleep=lambda s: None,
                           transport=httpx.MockTransport(lambda r: (_ for _ in ()).throw(httpx.ConnectError("x", request=r))))
    with pytest.raises(ServiceUnavailableError):
        client.request("GET", "/x")
