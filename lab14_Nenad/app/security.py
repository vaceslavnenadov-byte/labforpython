"""JWT-аутентификация и роли USER / ADMIN (доп. задания 1–2)."""

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.exceptions import AuthError, ForbiddenError
from app.models.train import User

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt, _ = stored.split("$")
    return hmac.compare_digest(hash_password(password, bytes.fromhex(salt)), stored)


def create_token(user: User) -> str:
    payload = {"sub": user.username, "role": user.role,
               "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                 db: Session = Depends(get_db)) -> User:
    if credentials is None:
        raise AuthError("Missing Authorization: Bearer <token>")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise AuthError("Invalid or expired token") from None
    user = db.scalar(select(User).where(User.username == payload["sub"]))
    if user is None:
        raise AuthError("User not found")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "ADMIN":
        raise ForbiddenError("Admin role required")
    return user
