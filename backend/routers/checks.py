"""Запуск проверок и управление результатами."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import CheckItem, CheckRun, Project, SessionLocal
from routers.auth import get_current_user
from services import check_engine, ntd_service

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

    # 0. Проверка актуальности НТД перед запуском проверки
    ntd_service.check_actual(session)

    files = [{"id": f.id, "filename": f.filename, "stored_path": f.stored_path,
              "file_type": f.file_type} for f in proj.files]
    results = check_engine.run_checks(files)

    run = CheckRun(project_id=payload.project_id, user_id=me.id,
                   mode=payload.mode, status="completed",
                   summary=f"Проверено {len(results)} проверок.")
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
        "items": [r.to_dict() for r in results],
        "ntd_expired": [{"number": d["number"], "issue": d["issue"]} for d in ntd],
    }


@router.get("/run/{run_id}")
def get_run(run_id: int, me=Depends(get_current_user),
            session: Session = Depends(get_session)):
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
def list_runs(project_id: int, me=Depends(get_current_user),
              session: Session = Depends(get_session)):
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