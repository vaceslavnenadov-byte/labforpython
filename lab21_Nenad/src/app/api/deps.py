"""Зависимости FastAPI: сессия БД, кэш, текущий пользователь, проверка роли."""

from collections.abc import Iterator

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.app.cache import Cache
from src.app.config import Settings
from src.app.exceptions import AuthException, ForbiddenException
from src.app.models import Role, User
from src.app.security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_cache(request: Request) -> Cache:
    return request.app.state.cache


def get_db(request: Request) -> Iterator[Session]:
    db = request.app.state.session_factory()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                 db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> User:
    if credentials is None:
        raise AuthException("Authorization header with Bearer token is required")
    payload = decode_token(credentials.credentials, settings.jwt_secret)
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise AuthException("User no longer exists")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != Role.ADMIN:
        raise ForbiddenException("Administrator role required")
    return user
