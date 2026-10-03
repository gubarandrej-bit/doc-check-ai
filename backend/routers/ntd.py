"""Управление базой НТД: просмотр, редактирование, проверка актуальности."""
import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import SessionLocal
from routers.auth import get_current_user, require_admin
from services import ntd_service

router = APIRouter(prefix="/ntd", tags=["ntd"])


def get_session():
    with SessionLocal() as s:
        yield s


class NtdCreate(BaseModel):
    number: str
    title: str
    doc_type: str | None = None
    effective_date: str | None = None
    status: str | None = None
    url: str | None = None
    note: str | None = None


class NtdUpdate(BaseModel):
    number: str | None = None
    title: str | None = None
    doc_type: str | None = None
    effective_date: str | None = None
    status: str | None = None
    url: str | None = None
    note: str | None = None


def _parse_date(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.datetime.strptime(s, fmt)
        except Exception:
            pass
    return None


@router.get("/")
def list_ntd(me=Depends(get_current_user), session: Session = Depends(get_session)):
    docs = ntd_service.list_docs(session)
    return [{"id": d.id, "number": d.number, "title": d.title, "doc_type": d.doc_type,
             "effective_date": str(d.effective_date.date()) if d.effective_date else None,
             "status": d.status, "url": d.url, "note": d.note} for d in docs]


@router.get("/actual-check")
def actual_check(me=Depends(get_current_user), session: Session = Depends(get_session)):
    return {"expired": ntd_service.check_actual(session)}


@router.post("/", status_code=201)
def create_ntd(payload: NtdCreate, admin=Depends(require_admin),
               session: Session = Depends(get_session)):
    d = ntd_service.create_doc(session, {
        "number": payload.number, "title": payload.title, "doc_type": payload.doc_type or "",
        "effective_date": _parse_date(payload.effective_date),
        "status": payload.status or "actual", "url": payload.url or "",
        "note": payload.note or "",
    })
    return {"id": d.id, "ok": True}


@router.put("/{doc_id}")
def update_ntd(doc_id: int, payload: NtdUpdate, admin=Depends(require_admin),
               session: Session = Depends(get_session)):
    data = payload.dict(exclude_unset=True)
    if "effective_date" in data:
        data["effective_date"] = _parse_date(data["effective_date"])
    d = ntd_service.update_doc(session, doc_id, data)
    if not d:
        raise HTTPException(status_code=404, detail="не найден")
    return {"ok": True}


@router.delete("/{doc_id}")
def delete_ntd(doc_id: int, admin=Depends(require_admin),
               session: Session = Depends(get_session)):
    if not ntd_service.delete_doc(session, doc_id):
        raise HTTPException(status_code=404, detail="не найден")
    return {"ok": True}