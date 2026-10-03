"""AI-слой: подключение моделей ИИ (локальных и облачных).

Правила, которые соблюдает система:
 1. При отсутствии исходных данных НИЧЕГО не придумывается — запрашивается недостающая информация.
 2. Проверки, которые не проводились, фиксируются с указанием причины.
 3. Ответы даются "как есть", без домыслов.
"""
from typing import Any

from config import (
    OLLAMA_BASE_URL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
)
from models import AiModel

SYSTEM_PROMPT = (
    "Ты — строгий инженер-проверщик проектной и рабочей документации по "
    "электрическим, слаботочным и противопожарным системам РФ. "
    "Анализируй ТОЛЬКО предоставленные данные. НИЧЕГО не придумывай и не интерпретируй сверх данных. "
    "Если данных недостаточно — прямо скажи, каких именно, и не выдавай выводы. "
    "Ссылайся на пункты НТД, которые указаны в данных. "
    "Отвечай кратко, структурно, на русском."
)


def _client(model: AiModel):
    """Создаёт httpx-клиент для выбранного провайдера."""
    import httpx
    if model.provider == "openrouter":
        key = model.api_key or OPENROUTER_API_KEY
        return httpx.Client(
            base_url=model.base_url or OPENROUTER_BASE_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "HTTP-Referer": "http://localhost",
                "X-Title": "doccheck",
            },
            timeout=120,
        )
    if model.provider == "ollama":
        return httpx.Client(base_url=model.base_url or OLLAMA_BASE_URL, timeout=180)
    if model.provider == "custom":
        return httpx.Client(base_url=model.base_url or "", timeout=120)
    return None


def chat(model: AiModel, messages: list[dict], temperature: float = 0.0) -> dict:
    """Возвращает {'text':..., 'model':..., 'ok':bool, 'error':...}."""
    client = _client(model)
    if client is None:
        return {"text": "", "ok": False, "error": "неподдерживаемый провайдер модели"}
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
    """Анализ документа. При отсутствии текста — честный отказ без выдумывания."""
    if not doc_text or not doc_text.strip():
        return {
            "ok": False,
            "error": "нет текста документа для анализа — недостающие данные",
            "text": "Анализ не проведён: исходные данные (текст документа) отсутствуют.",
        }
    msgs = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Документ:\n{doc_text[:12000]}\n\nВопрос: {question}"},
    ]
    return chat(model, msgs)


def select_model(session, model_id: int | None = None) -> AiModel | None:
    """Выбирает модель: по id, иначе — по умолчанию, иначе — первую активную."""
    if model_id:
        m = session.query(AiModel).get(model_id)
        if m and m.is_active:
            return m
    d = session.query(AiModel).filter_by(is_default=True, is_active=True).first()
    if d:
        return d
    return session.query(AiModel).filter_by(is_active=True).first()