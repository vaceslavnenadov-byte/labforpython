from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.app.api.deps import current_user, get_db, get_settings
from src.app.config import Settings
from src.app.models import User
from src.app.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from src.app.services.services import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def service(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> AuthService:
    return AuthService(db, settings.jwt_secret, settings.jwt_expire_minutes)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, auth: AuthService = Depends(service)):
    """Регистрация пассажира (роль USER)."""
    return auth.register(data)


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, auth: AuthService = Depends(service)):
    return TokenOut(access_token=auth.login(data.email, data.password))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user
