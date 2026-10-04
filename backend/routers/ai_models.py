"""Управление моделями ИИ: добавление/удаление через веб-интерфейс."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models import SessionLocal, AiModel
from routers.auth import get_current_user, require_admin

router = APIRouter(prefix="/ai-models", tags=["ai-models"])


def get_session():
    with SessionLocal() as s:
        yield s


class ModelCreate(BaseModel):
    name: str
    provider: str
    model_id: str
    mode: str = "cloud"
    capabilities: str = "text"   # "text" | "text vision"
    api_key: str | None = None
    base_url: str | None = None
    description: str | None = None
    is_default: bool = False


class ModelUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    model_id: str | None = None
    mode: str | None = None
    capabilities: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    description: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None


@router.get("/")
def list_models(me=Depends(get_current_user), session: Session = Depends(get_session)):
    ms = session.query(AiModel).order_by(AiModel.id).all()
    return [{"id": m.id, "name": m.name, "provider": m.provider, "model_id": m.model_id,
             "mode": m.mode, "is_default": m.is_default, "is_active": m.is_active,
             "capabilities": m.capabilities, "description": m.description} for m in ms]


@router.get("/plugins")
def list_plugins(me=Depends(get_current_user)):
    """Список ИИ-плагинов с их требованиями к модели.

    Нужен, чтобы администратор видел, какие модели и способности нужны
    для работы каждого плагина.
    """
    from services.ai_plugins import list_plugins as _lp
    return _lp()


@router.get("/capabilities")
def model_capabilities(model_id: int, session: Session = Depends(get_session)):
    """Определяет способности конкретной модели (явные или по имени)."""
    from services.ai_plugins.base import model_capabilities as _caps
    m = session.query(AiModel).get(model_id)
    if not m:
        raise HTTPException(status_code=404, detail="не найдена")
    return {"id": m.id, "model_id": m.model_id,
            "capabilities": sorted(_caps(m))}


@router.post("/", status_code=201)
def create_model(payload: ModelCreate, admin=Depends(require_admin),
                 session: Session = Depends(get_session)):
    if payload.is_default:
        session.query(AiModel).update({"is_default": False})
    m = AiModel(name=payload.name, provider=payload.provider, model_id=payload.model_id,
                mode=payload.mode, capabilities=payload.capabilities or "text",
                api_key=payload.api_key or "",
                base_url=payload.base_url or "", description=payload.description or "",
                is_default=payload.is_default)
    session.add(m)
    session.commit()
    session.refresh(m)
    return {"id": m.id, "ok": True}


@router.put("/{model_id}")
def update_model(model_id: int, payload: ModelUpdate, admin=Depends(require_admin),
                 session: Session = Depends(get_session)):
    m = session.query(AiModel).get(model_id)
    if not m:
        raise HTTPException(status_code=404, detail="не найдена")
    data = payload.dict(exclude_unset=True)
    if data.get("is_default"):
        session.query(AiModel).update({"is_default": False})
    for k, v in data.items():
        setattr(m, k, v)
    session.commit()
    return {"ok": True}


@router.delete("/{model_id}")
def delete_model(model_id: int, admin=Depends(require_admin),
                 session: Session = Depends(get_session)):
    m = session.query(AiModel).get(model_id)
    if not m:
        raise HTTPException(status_code=404, detail="не найдена")
    session.delete(m)
    session.commit()
    return {"ok": True}