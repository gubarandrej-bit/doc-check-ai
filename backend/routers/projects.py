"""Проекты и загрузка файлов."""
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE, UPLOAD_DIR
from models import Project, SessionLocal, UploadedFile
from routers.auth import get_current_user
from utils.parsers import detect_type

router = APIRouter(prefix="/projects", tags=["projects"])


def get_session():
    with SessionLocal() as s:
        yield s


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


@router.get("/")
def list_projects(me=Depends(get_current_user), session: Session = Depends(get_session)):
    out = []
    for p in session.query(Project).order_by(Project.created_at.desc()).all():
        out.append({
            "id": p.id, "name": p.name, "description": p.description,
            "created_at": str(p.created_at),
            "files": [{"id": f.id, "filename": f.filename, "file_type": f.file_type,
                       "size": f.size} for f in p.files],
        })
    return out


@router.post("/")
def create_project(payload: ProjectCreate, me=Depends(get_current_user),
                   session: Session = Depends(get_session)):
    p = Project(name=payload.name, description=payload.description or "")
    session.add(p)
    session.commit()
    session.refresh(p)
    return {"id": p.id, "name": p.name, "ok": True}


@router.post("/{project_id}/upload")
async def upload(project_id: int, me=Depends(get_current_user),
                 session: Session = Depends(get_session),
                 files: list[UploadFile] = File(...)):
    proj = session.query(Project).get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="проект не найден")
    saved = []
    for f in files:
        ext = os.path.splitext(f.filename)[1].lower().lstrip(".")
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"недопустимый формат: {f.filename}")
        content = await f.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"файл слишком большой: {f.filename}")
        fname = f"{uuid.uuid4().hex}_{f.filename}"
        path = UPLOAD_DIR / fname
        path.write_bytes(content)
        uf = UploadedFile(project_id=project_id, filename=f.filename,
                          stored_path=str(path), file_type=detect_type(f.filename),
                          size=len(content))
        session.add(uf)
        saved.append({"filename": f.filename, "file_type": uf.file_type, "size": len(content)})
    session.commit()
    return {"ok": True, "uploaded": saved}


@router.delete("/{project_id}/files/{file_id}")
def delete_file(project_id: int, file_id: int, me=Depends(get_current_user),
                session: Session = Depends(get_session)):
    uf = session.query(UploadedFile).get(file_id)
    if not uf or uf.project_id != project_id:
        raise HTTPException(status_code=404, detail="файл не найден")
    try:
        if os.path.exists(uf.stored_path):
            os.remove(uf.stored_path)
    except Exception:
        pass
    session.delete(uf)
    session.commit()
    return {"ok": True}