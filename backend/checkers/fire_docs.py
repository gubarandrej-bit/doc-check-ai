"""Проверка наличия раздела пожарной безопасности в документации (123-ФЗ)."""
from checkers.base import Checker, CheckResult


class FireDocsCompleteChecker(Checker):
    code = "FIRE_DOCS_COMPLETE"
    name = "Проверка наличия раздела пожарной безопасности (123-ФЗ)"
    category = "non-critical"
    ntd_refs = "123-ФЗ; ГОСТ Р 21.101-2026"

    def run(self, data):
        text = (data.get("doc_text") or "") + "\n" + (data.get("scheme_text") or "")
        if not text.strip():
            return self._not_performed(
                reason="Нет текстовой документации для проверки.",
                detail="Загрузите пояснительную записку или текстовое описание проекта.",
            )
        low = text.lower()
        hits = [kw for kw in ("пожарн", "сигнал", "оповещ", "сОУЭ", "123-фз", "пожаротуш")
                if kw in low]
        if not hits:
            return self._not_performed(
                reason="В тексте документации не найдено упоминаний пожарной безопасности.",
                detail="Проверьте, присутствует ли раздел по пожарной безопасности (123-ФЗ).",
            )
        return self._ok(
            detail=f"Упоминания пожарной безопасности найдены: {', '.join(hits)}.",
            evidence=[{"type": "keywords", "items": hits}],
        )