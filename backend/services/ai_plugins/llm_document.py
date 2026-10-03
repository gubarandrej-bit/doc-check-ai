"""Плагин ИИ: анализ текстовой проектной документации (PDF / DOC / DOCX) по НТД.

Как работает:
  1. Текст документа разбивается на части ограниченного размера.
  2. Каждая часть передаётся выбранной модели (OpenRouter / Ollama / custom).
  3. Модель возвращает структурированный JSON со ссылками на пункты НТД.
  4. Ответы собираются в один результат проверки.

Принципы, которые этот плагин не нарушает:
  - Модели предписано опираться ТОЛЬКО на переданный текст. Если данных мало —
    она обязана сказать об этом, а не достроить вывод.
  - Если ответ модели не удалось разобрать, проверка помечается как не проведённая
    с указанием причины. Ничего не додумывается.
  - Если модель недоступна или отключена, проверка не запускается, причина фиксируется.
"""
import json
import re

from services.ai_service import chat
from services.ai_plugins.base import CAP_TEXT, AIPlugin, PluginContext
from checkers.base import CheckResult

# Ограничения, чтобы одна проверка не уходила в бесконечный расход времени и токенов.
CHUNK_SIZE = 6000      # символов в одной части
CHUNK_OVERLAP = 400    # перекрытие между частями, чтобы не терять смысл на стыке
MAX_CHUNKS = 8         # максимум частей за один запуск

SYSTEM_PROMPT = (
    "Ты — строгий инженер-проверщик проектной и рабочей документации по "
    "электрическим, слаботочным и противопожарным системам Российской Федерации.\n"
    "Твоя задача — найти в предоставленном тексте конкретные отклонения от "
    "нормативно-технических требований.\n\n"
    "ЖЁСТКИЕ ПРАВИЛА:\n"
    "1. Используй ТОЛЬКО факты из предоставленного текста. НИЧЕГО не придумывай.\n"
    "2. Если текста недостаточно для вывода — верни пустой список issues и "
    "заполни поле insufficient_data строкой с описанием, чего именно не хватает.\n"
    "3. Не выдумывай номера пунктов НТД. Указывай только те, что реально применимы "
    "и следуют из текста.\n"
    "4. Каждое замечание подкрепляй прямой цитатой (поле quote) из текста. "
    "Если точной цитаты нет — не создавай замечание.\n"
    "5. Не повторяй одно и то же отклонение несколько раз.\n\n"
    "ОТВЕТ ДОЛЖЕН БЫТЬ СТРОГО JSON без пояснений вокруг:\n"
    '{"issues": [{"severity": "critical|non-critical", '
    '"comment": "что не так", "quote": "цитата из текста", '
    '"ntd": "пункт НТД или пустая строка"}], '
    '"insufficient_data": ""}'
)


def _split_chunks(text: str, size: int = CHUNK_SIZE,
                  overlap: int = CHUNK_OVERLAP, max_chunks: int = MAX_CHUNKS) -> list[str]:
    """Делит текст на части, стараясь резать по границам абзацев."""
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    pos = 0
    while pos < len(text) and len(chunks) < max_chunks:
        end = min(pos + size, len(text))
        if end < len(text):
            window = text.rfind("\n", pos + size // 2, end)
            if window > pos:
                end = window
        chunks.append(text[pos:end])
        if end >= len(text):
            break
        pos = end - overlap
    return chunks


def _extract_json(raw: str) -> dict | None:
    """Достаёт JSON-объект из ответа модели.

    Модели часто оборачивают JSON в markdown-блок ```json ... ``` или добавляют
    текст до/после. Здесь ищем первый сбалансированный объект, игнорируя
    фигурные скобки внутри строк.
    """
    if not raw:
        return None
    t = raw.strip()

    fence = re.search(r"```(?:json)?\s*(.+?)```", t, re.DOTALL | re.IGNORECASE)
    if fence:
        t = fence.group(1).strip()

    start = t.find("{")
    if start == -1:
        return None

    depth = 0
    in_str = False
    escaped = False
    for i in range(start, len(t)):
        ch = t[i]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(t[start:i + 1])
                except Exception:
                    return None
    return None


def _ntd_context(ntd_refs: list[dict], limit: int = 25) -> str:
    """Формирует перечень НТД, по которым модель ориентируется."""
    if not ntd_refs:
        return "(перечень НТД не передан — проверяй только внутренние противоречия документа)"
    lines = []
    for d in ntd_refs[:limit]:
        num = d.get("number", "")
        title = (d.get("title", "") or "")[:160]
        lines.append(f"- {num} {title}".strip())
    return "\n".join(lines)


class LlmDocumentChecker(AIPlugin):
    code = "AI_DOC_TEXT"
    name = "ИИ-анализ текстовой документации (PDF, DOC) по НТД"
    category = "non-critical"
    capability = CAP_TEXT
    description = (
        "Извлекает текст из PDF/DOC и передаёт его выбранной модели ИИ для поиска "
        "отклонений от НТД со ссылками на пункты и цитатами из документа."
    )
    ntd_refs = "Перечень НТД передаётся модели из базы данных НТД"

    def availability(self, ctx: PluginContext) -> tuple[bool, str]:
        ok, reason = super().availability(ctx)
        if not ok:
            return ok, reason
        if not ctx.doc_text:
            return False, (
                "Текстовая документация не найдена. Плагину нужен текст из PDF/DOC/DOCX; "
                "DWG и сканированные PDF без текстового слоя текста не дают."
            )
        return True, ""

    def run(self, ctx: PluginContext) -> CheckResult:
        chunks = _split_chunks(ctx.doc_text)
        if not chunks:
            return self._not_performed(
                reason="Текст документа пуст — анализировать нечего.",
                detail="Требуется текстовый слой PDF либо содержимое DOC/DOCX.",
            )

        ntd_ctx = _ntd_context(ctx.ntd_refs)
        issues: list[dict] = []
        insufficient: list[str] = []
        chunk_errors: list[str] = []
        analyzed = 0

        for idx, chunk in enumerate(chunks, start=1):
            user = (
                f"Перечень НТД, на которые нужно опираться:\n{ntd_ctx}\n\n"
                f"Часть документа {idx} из {len(chunks)}:\n"
                f"-----\n{chunk}\n-----\n\n"
                "Найди отклонения от НТД. Верни только JSON по схеме из системного промпта."
            )
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ]
            resp = chat(ctx.model, messages)

            if not resp.get("ok"):
                chunk_errors.append(
                    f"часть {idx}: {resp.get('error') or 'неизвестная ошибка модели'}"
                )
                continue

            data = _extract_json(resp.get("text", ""))
            if not isinstance(data, dict):
                chunk_errors.append(
                    f"часть {idx}: ответ модели не удалось разобрать как JSON — "
                    "результат по этой части не интерпретируется, чтобы не искажать смысл"
                )
                continue

            analyzed += 1
            for it in data.get("issues") or []:
                if not isinstance(it, dict):
                    continue
                comment = (it.get("comment") or "").strip()
                quote = (it.get("quote") or "").strip()
                if not comment:
                    continue
                # Замечание без цитаты не подтверждено текстом — не принимаем его.
                if not quote:
                    continue
                sev = (it.get("severity") or "non-critical").strip().lower()
                if sev not in ("critical", "non-critical"):
                    sev = "non-critical"
                issues.append({
                    "part": idx,
                    "severity": sev,
                    "comment": comment[:1000],
                    "quote": quote[:600],
                    "ntd": (it.get("ntd") or "").strip()[:300],
                })

            ins = (data.get("insufficient_data") or "").strip()
            if ins:
                insufficient.append(f"часть {idx}: {ins[:400]}")

        # Ни одна часть не разобралась — честно не проводим проверку.
        if analyzed == 0:
            return self._not_performed(
                reason="Ответ модели не удалось разобрать ни по одной части документа.",
                detail="; ".join(chunk_errors)[:800] or "модель вернула пустой или некорректный ответ",
            )

        critical = [i for i in issues if i["severity"] == "critical"]
        summary_parts = [
            f"Проанализировано частей: {analyzed} из {len(chunks)}.",
            f"Найдено замечаний: {len(issues)} (критических: {len(critical)}).",
        ]
        if chunk_errors:
            summary_parts.append(
                f"Не обработано частей: {len(chunk_errors)} — " + "; ".join(chunk_errors[:5])
            )

        if not issues:
            detail = " ".join(summary_parts) + " Замечаний по НТД не выявлено."
            if insufficient:
                detail += " Модель указала на неполноту данных: " + "; ".join(insufficient[:3])
            return self._ok(
                detail=detail,
                evidence=[{"type": "analyzed_chunks", "count": analyzed,
                           "insufficient": insufficient[:10]}] if insufficient else None,
            )

        return self._fail(
            detail=" ".join(summary_parts),
            evidence=[{"type": "issues", "items": issues[:60]}],
        )