"""Интеграционный тест: Client → TCP → Server → Service → Repository."""

import threading

import pytest

from client import HotelClient, udp_status
from repository import RoomRepository
from server import HotelServer
from service import RoomService, seed


@pytest.fixture
def server():
    service = RoomService(RoomRepository())
    seed(service)
    srv = HotelServer("127.0.0.1", 0, service)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    srv.started.wait(5)
    yield srv
    srv.shutdown()
    thread.join(5)


def test_full_cycle_over_tcp(server):
    with HotelClient("127.0.0.1", server.port) as client:
        assert client.request("ping")["data"]["message"] == "pong"
        created = client.request("create", {"number": "501", "room_type": "suite", "floor": 5,
                                            "price": 15000, "capacity": 2})
        assert created["status"] == "ok"
        room_id = created["data"]["id"]
        assert client.request("check_in", {"id": room_id, "guest": "Тест"})["data"]["is_free"] is False
        assert client.request("get", {"id": 999})["status"] == "error"
        assert client.request("unknown")["error"].startswith("Unknown command")


def test_several_clients_and_conflict(server):
    clients = [HotelClient("127.0.0.1", server.port) for _ in range(3)]
    for c in clients:
        c.connect()
    results = [c.request("check_in", {"id": 1, "guest": f"Гость {i}"})["status"] for i, c in enumerate(clients)]
    assert results.count("ok") == 1 and results.count("error") == 2
    for c in clients:
        c.close()


def test_udp_status(server):
    status = udp_status("127.0.0.1", server.port)
    assert status is not None and status["total"] == 6
