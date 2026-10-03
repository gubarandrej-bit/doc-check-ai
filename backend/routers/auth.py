"""Роутер аутентификации."""
import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import create_access_token, decode_token, verify_password
from models import SessionLocal, User

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


def get_session():
    with SessionLocal() as s:
        yield s


class LoginIn(BaseModel):
    login: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str
    user: dict


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, session: Session = Depends(get_session)):
    user = session.query(User).filter_by(login=payload.login).first()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="неверный логин или пароль")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    user.last_login = datetime.datetime.utcnow()
    session.commit()
    return TokenOut(access_token=token, token_type="bearer", user={
        "id": user.id, "login": user.login, "full_name": user.full_name, "role": user.role,
    })


@router.get("/me")
def me(credentials: HTTPAuthorizationCredentials = Depends(security),
       session: Session = Depends(get_session)):
    if not credentials:
        raise HTTPException(status_code=401, detail="нет токена")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="токен недействителен")
    user = session.query(User).get(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="пользователь не найден")
    return {"id": user.id, "login": user.login, "full_name": user.full_name,
            "role": user.role, "is_active": user.is_active}


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security),
                     session: Session = Depends(get_session)):
    if not credentials:
        raise HTTPException(status_code=401, detail="не авторизован")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="токен недействителен")
    user = session.query(User).get(int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="пользователь заблокирован или удалён")
    return user


def require_admin(user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="только для администратора")
    return user