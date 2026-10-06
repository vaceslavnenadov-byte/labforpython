import socket

import pytest

from exceptions import ProtocolError
from protocol import MessageReader, decode_message, encode_message, make_request, validate_request


def test_encode_decode_roundtrip():
    message = make_request("get", {"id": 5}, "abc")
    raw = encode_message(message)
    assert raw.endswith(b"\n")
    assert decode_message(raw.strip()) == message


@pytest.mark.parametrize("raw", [b"{bad", b"[1, 2]", b"\xff\xfe"])
def test_decode_invalid(raw):
    with pytest.raises(ProtocolError):
        decode_message(raw)


def test_validate_request_requires_command():
    with pytest.raises(ProtocolError):
        validate_request({"data": {}})
    assert validate_request({"command": "list"}) == ("list", {})


def test_reader_splits_stream_into_messages():
    left, right = socket.socketpair()
    with left, right:
        # два сообщения, разрезанные на произвольные куски
        payload = encode_message({"command": "a"}) + encode_message({"command": "b"})
        left.sendall(payload[:5])
        left.sendall(payload[5:])
        reader = MessageReader(right)
        assert reader.read()["command"] == "a"
        assert reader.read()["command"] == "b"
