"""Прикладной протокол: newline-delimited JSON.

Запрос:  {"request_id": "...", "command": "list", "data": {}}\n
Ответ:   {"request_id": "...", "status": "ok", "data": ...}\n
         {"request_id": "...", "status": "error", "error": "..."}\n
"""

import json
import socket

from exceptions import ProtocolError

ENCODING = "utf-8"
DELIMITER = b"\n"
MAX_MESSAGE_SIZE = 64 * 1024


def encode_message(message: dict) -> bytes:
    return json.dumps(message, ensure_ascii=False).encode(ENCODING) + DELIMITER


def decode_message(raw: bytes) -> dict:
    try:
        message = json.loads(raw.decode(ENCODING))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProtocolError(f"Invalid JSON: {error}") from error
    if not isinstance(message, dict):
        raise ProtocolError("Message must be a JSON object")
    return message


def make_request(command: str, data: dict | None = None, request_id: str | None = None) -> dict:
    request = {"command": command, "data": data or {}}
    if request_id:
        request["request_id"] = request_id
    return request


def validate_request(message: dict) -> tuple[str, dict]:
    if "command" not in message:
        raise ProtocolError("Missing required field: command")
    if not isinstance(message["command"], str):
        raise ProtocolError("Field 'command' must be a string")
    data = message.get("data", {})
    if not isinstance(data, dict):
        raise ProtocolError("Field 'data' must be an object")
    return message["command"], data


def ok(data, request_id=None) -> dict:
    return {"request_id": request_id, "status": "ok", "data": data}


def error(text: str, request_id=None) -> dict:
    return {"request_id": request_id, "status": "error", "error": text}


class MessageReader:
    """Собирает сообщения из потока байтов TCP: recv() может вернуть часть
    сообщения или сразу несколько сообщений."""

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.buffer = b""

    def read(self) -> dict | None:
        """Возвращает следующее сообщение или None, если соединение закрыто."""
        while DELIMITER not in self.buffer:
            if len(self.buffer) > MAX_MESSAGE_SIZE:
                raise ProtocolError("Message too large")
            chunk = self.sock.recv(4096)
            if not chunk:
                return None
            self.buffer += chunk
        line, self.buffer = self.buffer.split(DELIMITER, 1)
        return decode_message(line)
