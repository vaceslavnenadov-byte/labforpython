"""Пароли (PBKDF2) и JWT."""

import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta

import jwt

from src.app.exceptions import AuthException


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt_hex, _ = stored.split("$", 1)
    return hmac.compare_digest(hash_password(password, bytes.fromhex(salt_hex)), stored)


def create_token(user_id: int, role: str, secret: str, minutes: int) -> str:
    payload = {"sub": str(user_id), "role": role, "exp": datetime.now(UTC) + timedelta(minutes=minutes)}
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str, secret: str) -> dict:
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthException("Token expired") from None
    except jwt.PyJWTError:
        raise AuthException("Invalid token") from None
