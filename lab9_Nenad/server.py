"""
ЛР №9. TCP-сервер. Вариант 10 — Отель (сущность Room, спец. команда find_free).

Запуск:  python server.py [--host 127.0.0.1] [--port 5000]
UDP-статус доступен на порту port+1.
"""

import argparse
import json
import logging
import os
import socket
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from exceptions import ConflictError, HotelError, ProtocolError, RoomNotFoundError, ValidationError
from protocol import MessageReader, encode_message, error, ok, validate_request
from repository import RoomRepository
from service import RoomService, seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("hotel-server")

CLIENT_TIMEOUT = 120          # сек. бездействия клиента до отключения
RATE_LIMIT = (10, 10.0)       # не более 10 запросов за 10 секунд
HISTORY_SIZE = 20


class RateLimiter:
    def __init__(self, limit: int, period: float) -> None:
        self.limit, self.period = limit, period
        self.calls: deque[float] = deque()

    def allow(self) -> bool:
        now = time.monotonic()
        while self.calls and now - self.calls[0] > self.period:
            self.calls.popleft()
        if len(self.calls) >= self.limit:
            return False
        self.calls.append(now)
        return True


class HotelServer:
    def __init__(self, host: str, port: int, service: RoomService, max_workers: int = 10) -> None:
        self.host, self.port = host, port
        self.service = service
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.history: deque[dict] = deque(maxlen=HISTORY_SIZE)
        self.history_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.admin_token = os.getenv("HOTEL_ADMIN_TOKEN", "admin")
        self.started = threading.Event()
        self.connections: set[socket.socket] = set()
        self.connections_lock = threading.Lock()
        self.handlers = {
            "list": lambda d: [r.to_dict() for r in self.service.list_rooms()],
            "get": lambda d: self.service.get_room(self._int(d, "id")).to_dict(),
            "create": lambda d: self.service.create_room(d).to_dict(),
            "update": lambda d: self.service.update_room(self._int(d, "id"),
                                                         {k: v for k, v in d.items() if k != "id"}).to_dict(),
            "delete": self._delete,
            "find_free": lambda d: [r.to_dict() for r in self.service.find_free_rooms(
                d.get("room_type"), d.get("min_capacity", 1), d.get("max_price"))],
            "check_in": lambda d: self.service.check_in(self._int(d, "id"), d.get("guest", "")).to_dict(),
            "check_out": lambda d: self.service.check_out(self._int(d, "id")).to_dict(),
            "stats": lambda d: self.service.statistics(),
            "ping": lambda d: {"message": "pong", "server_time": time.time()},
            "history": lambda d: list(self.history),
            "sleep": self._sleep,
        }

    @staticmethod
    def _int(data: dict, key: str) -> int:
        if key not in data:
            raise ValidationError(f"Missing required field: {key}")
        try:
            return int(data[key])
        except (TypeError, ValueError):
            raise ValidationError(f"Field '{key}' must be an integer") from None

    def _delete(self, data: dict) -> dict:
        room_id = self._int(data, "id")
        self.service.delete_room(room_id)
        return {"deleted": room_id}

    @staticmethod
    def _sleep(data: dict) -> dict:
        """Отладочная команда для демонстрации тайм-аута клиента."""
        seconds = min(float(data.get("seconds", 1)), 30)
        time.sleep(seconds)
        return {"slept": seconds}

    # ---------- обработка запроса (без сети — удобно тестировать) ----------
    def handle_request(self, message: dict, client: str) -> dict:
        request_id = message.get("request_id")
        try:
            command, data = validate_request(message)
            logger.info("Command from %s: %s %s", client, command, data or "")
            with self.history_lock:
                self.history.append({"client": client, "command": command, "time": time.strftime("%H:%M:%S")})
            if command == "shutdown":
                if data.get("token") != self.admin_token:
                    return error("Forbidden: invalid admin token", request_id)
                threading.Thread(target=self.shutdown, daemon=True).start()
                return ok({"message": "server is shutting down"}, request_id)
            handler = self.handlers.get(command)
            if handler is None:
                return error(f"Unknown command: {command}", request_id)
            result = handler(data)
            logger.info("Command %s from %s: OK", command, client)
            return ok(result, request_id)
        except (ProtocolError, ValidationError, RoomNotFoundError, ConflictError, HotelError) as exc:
            logger.warning("Bad request from %s: %s", client, exc)
            return error(str(exc), request_id)
        except Exception:  # сервер не должен падать из-за одного запроса
            logger.exception("Unexpected error while handling request from %s", client)
            return error("Internal server error", request_id)

    # ---------- сеть ----------
    def handle_client(self, conn: socket.socket, address) -> None:
        client = f"{address[0]}:{address[1]}"
        logger.info("Client connected: %s", client)
        conn.settimeout(CLIENT_TIMEOUT)
        limiter = RateLimiter(*RATE_LIMIT)
        reader = MessageReader(conn)
        with self.connections_lock:
            self.connections.add(conn)
        try:
            with conn:
                while not self.stop_event.is_set():
                    try:
                        message = reader.read()
                    except ProtocolError as exc:
                        conn.sendall(encode_message(error(str(exc))))
                        continue
                    if message is None:
                        break
                    if not limiter.allow():
                        response = error("Rate limit exceeded: max 10 requests per 10 seconds",
                                         message.get("request_id"))
                    else:
                        response = self.handle_request(message, client)
                    conn.sendall(encode_message(response))
        except socket.timeout:
            logger.info("Client %s timed out (idle %ss)", client, CLIENT_TIMEOUT)
        except (ConnectionResetError, BrokenPipeError):
            logger.warning("Connection with %s was reset", client)
        except OSError:
            pass  # сокет закрыт сервером при остановке
        finally:
            with self.connections_lock:
                self.connections.discard(conn)
            logger.info("Client disconnected: %s", client)

    def serve_udp(self) -> None:
        """UDP: быстрый запрос статуса. Потеря датаграммы некритична — клиент спросит снова."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.bind((self.host, self.port + 1))
            udp.settimeout(0.5)
            while not self.stop_event.is_set():
                try:
                    payload, address = udp.recvfrom(1024)
                except socket.timeout:
                    continue
                if payload.strip() == b"status":
                    udp.sendto(json.dumps(self.service.statistics()).encode(), address)

    def serve_forever(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            self.port = server.getsockname()[1]
            threading.Thread(target=self.serve_udp, daemon=True).start()
            server.listen()
            server.settimeout(0.5)   # чтобы периодически проверять stop_event
            logger.info("Server started on %s:%s (UDP status on %s)", self.host, self.port, self.port + 1)
            self.started.set()
            while not self.stop_event.is_set():
                try:
                    conn, address = server.accept()
                except socket.timeout:
                    continue
                self.executor.submit(self.handle_client, conn, address)
        logger.info("Stopped accepting new clients, closing active sessions...")
        with self.connections_lock:
            for conn in self.connections:
                try:
                    conn.shutdown(socket.SHUT_RD)  # текущий запрос будет дообработан
                except OSError:
                    pass
        self.executor.shutdown(wait=True)
        logger.info("Server stopped")

    def shutdown(self) -> None:
        logger.info("Graceful shutdown requested")
        self.stop_event.set()


def main() -> None:
    parser = argparse.ArgumentParser(description="Hotel TCP server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    service = RoomService(RoomRepository())
    seed(service)
    server = HotelServer(args.host, args.port, service)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
