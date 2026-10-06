import os

os.environ["SERVICE_AUTOSTART"] = "0"     # приложения создаются в тестах явно, с тестовыми БД

import httpx  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def transport_to(test_client: TestClient) -> httpx.MockTransport:
    """HTTP-транспорт, который вместо сети вызывает другое приложение в памяти."""
    def handler(request: httpx.Request) -> httpx.Response:
        response = test_client.request(request.method, request.url.path, params=request.url.params,
                                       content=request.content, headers={"Content-Type": "application/json"})
        return httpx.Response(response.status_code, content=response.content, headers=response.headers)
    return httpx.MockTransport(handler)


def down_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)
    return httpx.MockTransport(handler)
