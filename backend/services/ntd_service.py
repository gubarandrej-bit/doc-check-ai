"""Служба работы с НТД: проверка актуальности, CRUD."""
import datetime
from sqlalchemy.orm import Session
from models import NtdDocument


def check_actual(session: Session) -> list[dict]:
    """Возвращает список устаревших/отменённых документов на текущую дату."""
    today = datetime.date.today()
    out = []
    for d in session.query(NtdDocument).order_by(NtdDocument.number).all():
        status = d.status or "actual"
        eff = d.effective_date.date() if d.effective_date else None
        if status == "expired" or status == "superseded":
            out.append({"id": d.id, "number": d.number, "title": d.title,
                        "status": status, "effective_date": eff, "issue": "документ помечен как отменённый/заменённый"})
            continue
        if eff and eff < today:
            d.status = "expired"
            session.add(d)
            out.append({"id": d.id, "number": d.number, "title": d.title,
                        "status": "expired", "effective_date": eff,
                        "issue": f"дата введения {eff} старше текущей даты {today}"})
    session.commit()
    return out


def list_docs(session: Session):
    return session.query(NtdDocument).order_by(NtdDocument.number).all()


def create_doc(session: Session, payload: dict) -> NtdDocument:
    d = NtdDocument(**payload)
    session.add(d)
    session.commit()
    session.refresh(d)
    return d


def update_doc(session: Session, doc_id: int, payload: dict) -> NtdDocument | None:
    d = session.query(NtdDocument).get(doc_id)
    if not d:
        return None
    for k, v in payload.items():
        if v is not None:
            setattr(d, k, v)
    session.commit()
    session.refresh(d)
    return d


def delete_doc(session: Session, doc_id: int) -> bool:
    d = session.query(NtdDocument).get(doc_id)
    if not d:
        return False
    session.delete(d)
    session.commit()
    return True