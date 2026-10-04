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


def _unpack_zip(zip_path: str) -> tuple[list[tuple[str, str, int]], list[str]]:
    """Распаковывает архив в каталог загрузок.

    Возвращает (список файлов, пояснения). Пояснения важны: если часть архива
    пропущена, пользователь должен знать об этом, а не получить молчаливую
    неполную проверку.

    Ограничения по безопасности:
      - запись строго внутрь UPLOAD_DIR (защита от путей вида ../../etc/passwd);
      - служебные файлы macOS и вложенные архивы не распаковываются;
      - число файлов и суммарный объём распакованных данных ограничены.
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