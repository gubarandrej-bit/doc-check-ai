"""Запуск проверок и управление результатами."""
import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models import (SessionLocal, Project, UploadedFile, CheckRun, CheckItem,
                    NtdDocument)
from routers.auth import get_current_user
from services import ai_service
from services import check_engine
from services import ntd_service

router = APIRouter(prefix="/checks", tags=["checks"])


def get_session():
    with SessionLocal() as s:
        yield s


class RunIn(BaseModel):
    project_id: int
    mode: str = "local"
    model_id: int | None = None


@router.post("/run")
def run_check(payload: RunIn, me=Depends(get_current_user),
              session: Session = Depends(get_session)):
    proj = session.query(Project).get(payload.project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="проект не найден")

    # 0. Проверка актуальности НТД перед запуском
    ntd_service.check_actual(session)

    # 1. Выбор модели ИИ. Если модель не выбрана, плагины ИИ не пропускаются
    #    молча — каждый вернёт not_performed с причиной.
    model = None
    if payload.model_id is not None:
        model = ai_service.select_model(session, payload.model_id)

    # 2. Перечень НТД передаётся плагинам, чтобы ссылки на пункты брались
    #    из базы, а не выдумывались моделью.
    ntd_list = [{"number": d.number, "title": d.title, "status": d.status}
                for d in session.query(NtdDocument).order_by(NtdDocument.number).all()]

    files = [{"id": f.id, "filename": f.filename, "stored_path": f.stored_path,
              "file_type": f.file_type} for f in proj.files]
    results = check_engine.run_checks(files, model=model,
                                      ntd_refs=ntd_list,
                                      mode=payload.mode)

    passed = sum(1 for r in results if r.status == "passed")
    failed = sum(1 for r in results if r.status == "failed")
    skipped = sum(1 for r in results if r.status == "not_performed")
    run = CheckRun(project_id=payload.project_id, user_id=me.id,
                   mode=payload.mode, status="completed",
                   summary=(f"Проверок: {len(results)}. Пройдено: {passed}. "
                            f"Нарушений: {failed}. Не проведено: {skipped}."))
    session.add(run)
    session.commit()
    session.refresh(run)
    for r in results:
        session.add(CheckItem(check_run_id=run.id, code=r.code, name=r.name,
                              category=r.category, status=r.status,
                              detail=r.detail, ntd_refs=r.ntd_refs,
                              reason_skipped=r.reason_skipped))
    session.commit()

    ntd = ntd_service.check_actual(session)
    return {
        "run_id": run.id, "status": run.status, "mode": payload.mode,
        "model": ({"id": model.id, "name": model.name,
                   "capabilities": model.capabilities} if model else None),
        "summary": {"total": len(results), "passed": passed,
                    "failed": failed, "not_performed": skipped},
        "items": [r.to_dict() for r in results],
        "ntd_expired": [{"number": d["number"], "issue": d["issue"]} for d in ntd],
    }


@router.get("/run/{run_id}")
def get_run(run_id: int, session: Session = Depends(get_session)):
    run = session.query(CheckRun).get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="не найдено")
    return {
        "run_id": run.id, "project_id": run.project_id, "mode": run.mode,
        "status": run.status, "summary": run.summary, "created_at": str(run.created_at),
        "items": [{"id": i.id, "code": i.code, "name": i.name, "category": i.category,
                   "status": i.status, "detail": i.detail, "ntd_refs": i.ntd_refs,
                   "reason_skipped": i.reason_skipped} for i in run.items],
    }


@router.get("/project/{project_id}")
def list_runs(project_id: int, session: Session = Depends(get_session)):
    runs = session.query(CheckRun).filter_by(project_id=project_id).order_by(CheckRun.created_at.desc()).all()
    return [{"run_id": r.id, "mode": r.mode, "status": r.status,
             "created_at": str(r.created_at), "items_count": len(r.items)} for r in runs]


@router.delete("/run/{run_id}")
def delete_run(run_id: int, me=Depends(get_current_user),
               session: Session = Depends(get_session)):
    run = session.query(CheckRun).get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="не найдено")
    session.delete(run)
    session.commit()
    return {"ok": True}