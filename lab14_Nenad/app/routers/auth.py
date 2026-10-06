from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import AuthError, ConflictError
from app.models.train import User
from app.schemas.auth import Token, UserCreate, UserResponse
from app.security import create_token, current_user, hash_password, verify_password

router = APIRouter(tags=["Авторизация"])


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             summary="Регистрация (первый пользователь становится ADMIN)")
def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.username == data.username)):
        raise ConflictError("Username already taken")
    role = "ADMIN" if db.scalar(select(func.count(User.id))) == 0 else "USER"
    user = User(username=data.username, password_hash=hash_password(data.password), role=role)
    db.add(user)
    db.commit()
    return UserResponse(id=user.id, username=user.username, role=user.role)


@router.post("/auth/login", response_model=Token, summary="Вход, получение JWT")
def login(data: UserCreate, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == data.username))
    if user is None or not verify_password(data.password, user.password_hash):
        raise AuthError("Invalid username or password")
    return Token(access_token=create_token(user))


@router.get("/profile", response_model=UserResponse, summary="Текущий пользователь (нужен токен)")
def profile(user: User = Depends(current_user)):
    return UserResponse(id=user.id, username=user.username, role=user.role)
