"""Проекты и загрузка файлов."""
import os
import shutil
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel

from config import (ALLOWED_EXTENSIONS, MAX_FILE_SIZE, UPLOAD_DIR,
                    ZIP_MAX_FILES, ZIP_MAX_TOTAL_SIZE)
from models import SessionLocal, Project, UploadedFile
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


def _unpack_zip(zip_path: str) -> tuple[list[tuple[str, str, int]], list[str]]:
    """Распаковывает архив в каталог загрузок.

    Возвращает (список файлов, пояснения). Пояснения важны: если часть архива
    пропущена, пользователь должен знать об этом, а не получить молчаливую
    неполную проверку.

    Ограничения по безопасности:
      - запись строго внутрь UPLOAD_DIR (защита от путей вида ../../etc/passwd);
      - служебные файлы macOS и вложенные архивы не распаковываются;
      - число файлов и суммарный распакованный объём ограничены, чтобы
        небольшой архив не распаковался в десятки гигабайт.
    """
    extracted: list[tuple[str, str, int]] = []
    notes: list[str] = []
    root = Path(UPLOAD_DIR).resolve()
    total = 0

    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        return [], ["файл не является корректным zip-архивом"]

    with zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            # Служебные файлы macOS — мусор, не документ.
            if "__MACOSX/" in name or os.path.basename(name) == ".DS_Store":
                continue
            ext = os.path.splitext(name)[1].lower().lstrip(".")
            if ext == "zip":
                notes.append(f"{name}: вложенный архив не распаковывается")
                continue
            if ext not in ALLOWED_EXTENSIONS:
                notes.append(f"{name}: неподдерживаемый формат, пропущен")
                continue

            if len(extracted) >= ZIP_MAX_FILES:
                notes.append(f"остановлено: предел в {ZIP_MAX_FILES} файлов на архив")
                break

            size = info.file_size
            if total + size > ZIP_MAX_TOTAL_SIZE:
                notes.append(
                    f"остановлено: предел распакованного объёма "
                    f"{ZIP_MAX_TOTAL_SIZE // (1024 * 1024)} МБ"
                )
                break

            # Ключевая проверка безопасности: итоговый путь обязан остаться
            # внутри каталога загрузок.
            base = os.path.basename(name)
            target = (root / base).resolve()
            if not str(target).startswith(str(root) + os.sep):
                notes.append(f"{name}: путь вне каталога загрузок, пропущен")
                continue

            if target.exists():
                notes.append(f"{base}: файл с таким именем уже загружен, пропущен")
                continue

            try:
                with zf.open(info) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst, length=1024 * 1024)
            except Exception as e:
                notes.append(f"{name}: не удалось распаковать ({type(e).__name__})")
                continue

            written = target.stat().st_size
            if written > MAX_FILE_SIZE:
                target.unlink(missing_ok=True)
                notes.append(f"{base}: файл больше допустимых {MAX_FILE_SIZE // (1024 * 1024)} МБ, пропущен")
                continue

            total += written
            extracted.append((base, str(target), written))

    if not extracted and not notes:
        notes.append("архив пуст")
    return extracted, notes


@router.post("/{project_id}/upload")
async def upload(project_id: int, me=Depends(get_current_user),
                 session: Session = Depends(get_session),
                 files: list[UploadFile] = File(...)):
    proj = session.query(Project).get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="проект не найден")
    saved = []
    notes = []
    for f in files:
        ext = os.path.splitext(f.filename)[1].lower().lstrip(".")
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"недопустимый формат: {f.filename}")
        content = await f.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"файл слишком большой: {f.filename}")

        if ext == "zip":
            # Архив распаковываем, а файлы из него регистрируем как обычные
            # загрузки: иначе содержимое никогда не попадёт в проверку.
            tmp = UPLOAD_DIR / f"{uuid.uuid4().hex}_{f.filename}"
            tmp.write_bytes(content)
            extracted, why = _unpack_zip(str(tmp))
            tmp.unlink(missing_ok=True)
            if not extracted:
                raise HTTPException(
                    status_code=400,
                    detail=f"из архива {f.filename} не удалось извлечь ни одного "
                           f"поддерживаемого файла: {'; '.join(why) or 'причина не установлена'}")
            notes.extend(why)
            for name, path, size in extracted:
                uf = UploadedFile(project_id=project_id, filename=name,
                                  stored_path=path, file_type=detect_type(name), size=size)
                session.add(uf)
                saved.append({"filename": name, "file_type": uf.file_type,
                              "size": size, "from_archive": f.filename})
            continue

        fname = f"{uuid.uuid4().hex}_{f.filename}"
        path = UPLOAD_DIR / fname
        path.write_bytes(content)
        uf = UploadedFile(project_id=project_id, filename=f.filename,
                          stored_path=str(path), file_type=detect_type(f.filename),
                          size=len(content))
        session.add(uf)
        saved.append({"filename": f.filename, "file_type": uf.file_type, "size": len(content)})
    session.commit()
    out = {"ok": True, "uploaded": saved}
    if notes:
        out["notes"] = notes
    return out


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