"""AI-слой: подключение моделей ИИ (локальных и облачных).

Правила, которые соблюдает система (как ты прописал):
 1. При отсутствии исходных данных НИЧЕГО не придумывается — запрашивается недостающая информация.
 2. Проверки, которые не проводились, фиксируются с указанием причины.
 3. Ответы даются "как есть", без домыслов.
"""
from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

from config import (
    AI_DEFAULT_MODEL, AI_DEFAULT_PROVIDER, OLLAMA_BASE_URL,
    OPENROUTER_API_KEY, OPENROUTER_BASE_URL, MODE,
)

if TYPE_CHECKING:  # ORM-модель нужна только для подсказок типов
    from models import AiModel

SYSTEM_PROMPT = (
    "Ты — строгий инженер-проверщик проектной и рабочей документации по "
    "электрическим, слаботочным и противопожарным системам РФ. "
    "Анализируй ТОЛЬКО предоставленные данные. НИЧЕГО не придумывай и не интерпретируй сверх данных. "
    "Если данных недостаточно — прямо скажи, каких именно, и не выдавай выводы. "
    "Ссылайся на пункты НТД, которые указаны в данных. "
    "Отвевай кратко, структурно, на русском."
)


def _client(model: AiModel):
    """Создаёт httpx-клиент для выбранного провайдера."""
    try:
        import httpx
    except Exception:
        # Без httpx работа с моделями невозможна — сообщаем это прямо,
        # чтобы причина была понятна оператору, а не пряталась за трассировкой.
        return None
    if model is None:
        return None
    if model.provider == "openrouter":
        key = model.api_key or OPENROUTER_API_KEY
        return httpx.Client(base_url=model.base_url or OPENROUTER_BASE_URL,
                            headers={"Authorization": f"Bearer {key}",
                                     "HTTP-Referer": "http://localhost",
                                     "X-Title": "doccheck"}, timeout=120)
    if model.provider == "ollama":
        return httpx.Client(base_url=model.base_url or OLLAMA_BASE_URL, timeout=180)
    if model.provider == "custom":
        return httpx.Client(base_url=model.base_url or "", timeout=120)
    return None


def chat(model: AiModel, messages: list[dict], temperature: float = 0.0) -> dict:
    """Возвращает {'text':..., 'model':..., 'ok':bool, 'error':...}."""
    client = _client(model)
    if client is None:
        if model is None:
            return {"text": "", "ok": False, "error": "модель не выбрана"}
        try:
            import httpx  # noqa: F401
        except Exception:
            return {"text": "", "ok": False,
                    "error": "библиотека httpx не установлена — обращение к моделям ИИ "
                             "невозможно (установите: pip install -r requirements.txt)"}
        return {"text": "", "ok": False,
                "error": f"неподдерживаемый провайдер модели: {model.provider!r}"}
    try:
        if model.provider == "ollama":
            r = client.post("/api/chat", json={
                "model": model.model_id, "messages": messages,
                "stream": False, "options": {"temperature": temperature},
            })
            r.raise_for_status()
            data = r.json()
            return {"text": data.get("message", {}).get("text", ""), "model": model.model_id, "ok": True}
        # openrouter / custom (OpenAI-совместимый)
        r = client.post("/chat/completions", json={
            "model": model.model_id, "messages": messages,
            "temperature": temperature,
        })
        r.raise_for_status()
        data = r.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"text": text, "model": data.get("model", model.model_id), "ok": True}
    except Exception as e:
        return {"text": "", "ok": False, "error": f"{type(e).__name__}: {e}"}


def analyze_document(model: AiModel, doc_text: str, question: str) -> dict:
    if not doc_text or not doc_text.strip():
        return {"ok": False, "error": "нет текста документа для анализа — недостающие данные",
                "text": "Анализ не проведён: исходные данные (текст документа) отсутствуют."}
    msgs = [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Документ:\n{doc_text[:12000]}\n\nВопрос: {question}"}]
    return chat(model, msgs)


def _image_block(image_path: str) -> dict:
    """Готовит изображение в виде data URL для OpenAI-совместимого формата."""
    import base64
    with open(image_path, "rb") as f:
        raw = f.read()
    ext = os.path.splitext(image_path)[1].lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "png")
    return {"type": "image_url",
            "image_url": {"url": f"data:image/{mime};base64,{base64.b64encode(raw).decode()}"}}


def chat_multimodal(model: AiModel, image_path: str, system_prompt: str,
                    user_text: str = "") -> dict:
    """Отправляет изображение + текст модели, умеющей работать с картинками.

    Только для провайдеров с OpenAI-совместимым форматом (OpenRouter, custom, Ollama).
    Возвращает ту же структуру, что и chat().
    """
    if not image_path or not os.path.exists(image_path):
        return {"text": "", "ok": False,
                "error": "изображение чертежа не найдено — vision-анализ не выполнялся"}
    if model is None:
        return {"text": "", "ok": False, "error": "модель не выбрана"}
    try:
        import httpx  # noqa: F401
    except Exception:
        return {"text": "", "ok": False,
                "error": "библиотека httpx не установлена — vision-анализ невозможен "
                         "(установите: pip install -r requirements.txt)"}
    if model.provider == "ollama":
        # У Ollama свой формат с images в base64.
        import base64
        try:
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
        except Exception as e:
            return {"text": "", "ok": False, "error": f"не удалось прочитать изображение: {e}"}
        client = _client(model)
        if client is None:
            return {"text": "", "ok": False, "error": "не удалось создать клиент Ollama"}
        try:
            r = client.post("/api/chat", json={
                "model": model.model_id,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text, "images": [b64]},
                ],
                "stream": False, "options": {"temperature": 0.0},
            })
            r.raise_for_status()
            data = r.json()
            return {"text": data.get("message", {}).get("text", ""),
                    "model": model.model_id, "ok": True}
        except Exception as e:
            return {"text": "", "ok": False, "error": f"{type(e).__name__}: {e}"}

    client = _client(model)
    if client is None:
        return {"text": "", "ok": False, "error": "неподдерживаемый провайдер модели"}
    content = [{"type": "text", "text": user_text or "Проанализируй чертёж."},
               _image_block(image_path)]
    try:
        r = client.post("/chat/completions", json={
            "model": model.model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            "temperature": 0.0,
        })
        r.raise_for_status()
        data = r.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"text": text, "model": data.get("model", model.model_id), "ok": True}
    except Exception as e:
        return {"text": "", "ok": False, "error": f"{type(e).__name__}: {e}"}


def select_model(session, model_id: int | None = None) -> AiModel | None:
    from models import AiModel  # локальный импорт: не тянет ORM в весь ИИ-слой

    if model_id:
        m = session.query(AiModel).get(model_id)
        if m and m.is_active:
            return m
    d = session.query(AiModel).filter_by(is_default=True, is_active=True).first()
    if d:
        return d
    return session.query(AiModel).filter_by(is_active=True).first()