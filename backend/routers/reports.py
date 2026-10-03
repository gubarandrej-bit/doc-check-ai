"""Генерация и выгрузка отчётов (doc/xls), выгрузка/удаление результатов проверок."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import CheckRun, Project, SessionLocal
from routers.auth import get_current_user
from services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


def get_session():
    with SessionLocal() as s:
        yield s


class ReportGenIn(BaseModel):
    run_id: int
    format: str = "docx"  # docx | xlsx
    include_acts: bool = True


@router.post("/generate")
def generate(payload: ReportGenIn, me=Depends(get_current_user),
             session: Session = Depends(get_session)):
    run = session.query(CheckRun).get(payload.run_id)
    if not run:
        raise HTTPException(status_code=404, detail="проверка не найдена")
    proj = session.query(Project).get(run.project_id)
    items = [{"code": i.code, "name": i.name, "category": i.category, "status": i.status,
              "detail": i.detail, "ntd_refs": i.ntd_refs, "reason_skipped": i.reason_skipped}
             for i in run.items]
    acts = {}
    if payload.include_acts and proj:
        spec_rows = []
        for f in proj.files:
            if f.file_type == "xls":
                from utils.parsers import parse_xls
                parsed = parse_xls(f.stored_path)
                if parsed:
                    for sheet, rows in parsed.get("sheets", {}).items():
                        if "специф" in sheet.lower() or "материал" in sheet.lower():
                            spec_rows = rows
        acts["spec_rows"] = spec_rows
    if payload.format == "xlsx":
        path = report_service.generate_xls(run.id, proj.name if proj else "", items, run.summary, acts)
    else:
        path = report_service.generate_docx(run.id, proj.name if proj else "", items, run.summary)
    return {"ok": True, "path": path, "format": payload.format}


@router.get("/run/{run_id}")
def export_run(run_id: int, me=Depends(get_current_user),
               session: Session = Depends(get_session)):
    run = session.query(CheckRun).get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="не найдено")
    items = [{"id": i.id, "code": i.code, "name": i.name, "category": i.category,
              "status": i.status, "detail": i.detail, "ntd_refs": i.ntd_refs,
              "reason_skipped": i.reason_skipped} for i in run.items]
    return {"run_id": run.id, "project_id": run.project_id, "mode": run.mode,
            "status": run.status, "summary": run.summary, "created_at": str(run.created_at),
            "items": items}


@router.delete("/run/{run_id}")
def delete_results(run_id: int, me=Depends(get_current_user),
                   session: Session = Depends(get_session)):
    run = session.query(CheckRun).get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="не найдено")
    session.delete(run)
    session.commit()
    return {"ok": True}