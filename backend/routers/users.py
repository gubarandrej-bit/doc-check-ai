"""Админка: управление пользователями."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_password_hash
from models import SessionLocal, User
from routers.auth import get_current_user, require_admin

router = APIRouter(prefix="/users", tags=["users"])


def get_session():
    with SessionLocal() as s:
        yield s


class UserCreate(BaseModel):
    login: str
    password: str
    full_name: str = ""
    role: str = "user"


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    password: str | None = None
    is_active: bool | None = None


@router.get("/")
def list_users(_=Depends(require_admin), session: Session = Depends(get_session)):
    users = session.query(User).order_by(User.login).all()
    return [{"id": u.id, "login": u.login, "full_name": u.full_name, "role": u.role,
             "is_active": u.is_active, "created_at": str(u.created_at)} for u in users]


@router.post("/")
def create_user(payload: UserCreate, _=Depends(require_admin), session: Session = Depends(get_session)):
    if session.query(User).filter_by(login=payload.login).first():
        raise HTTPException(status_code=400, detail="логин уже занят")
    u = User(login=payload.login, password_hash=get_password_hash(payload.password),
             full_name=payload.full_name,
             role=payload.role if payload.role in ("admin", "user") else "user")
    session.add(u)
    session.commit()
    session.refresh(u)
    return {"id": u.id, "login": u.login, "role": u.role, "ok": True}


@router.put("/{user_id}")
def update_user(user_id: int, payload: UserUpdate, _=Depends(require_admin),
                session: Session = Depends(get_session)):
    u = session.query(User).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="не найден")
    if payload.full_name is not None:
        u.full_name = payload.full_name
    if payload.role is not None:
        u.role = payload.role
    if payload.password:
        u.password_hash = get_password_hash(payload.password)
    if payload.is_active is not None:
        u.is_active = payload.is_active
    session.commit()
    return {"ok": True}


@router.delete("/{user_id}")
def delete_user(user_id: int, me=Depends(get_current_user), session: Session = Depends(get_session)):
    if me.id == user_id:
        raise HTTPException(status_code=400, detail="нельзя удалить себя")
    u = session.query(User).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="не найден")
    if u.role == "admin":
        admins = session.query(User).filter_by(role="admin", is_active=True).count()
        if admins <= 1:
            raise HTTPException(status_code=400, detail="нельзя удалить единственного администратора")
    session.delete(u)
    session.commit()
    return {"ok": True}