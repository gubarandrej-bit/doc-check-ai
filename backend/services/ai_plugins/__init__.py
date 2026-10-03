"""Реестр плагинов ИИ-анализа.

Здесь собираются все плагины и запускаются в одном месте. Ключевое правило:
плагин, который не может быть выполнен, НЕ пропускается молча — он возвращает
not_performed с конкретной причиной. Пользователь всегда видит, что именно
не было проверено и почему.
"""
from checkers.base import CheckResult
from services.ai_plugins.base import AIPlugin, CAP_TEXT, CAP_VISION, PluginContext
from services.ai_plugins.dwg_recognize import CadStructureChecker, DwgVisionChecker
from services.ai_plugins.llm_document import LlmDocumentChecker

# Порядок важен: сначала детерминированный разбор, потом смысловой анализ ИИ.
ALL_PLUGINS: list[type[AIPlugin]] = [
    CadStructureChecker,
    LlmDocumentChecker,
    DwgVisionChecker,
]


def list_plugins() -> list[dict]:
    """Описание плагинов для веб-интерфейса."""
    out = []
    for cls in ALL_PLUGINS:
        out.append({
            "code": cls.code,
            "name": cls.name,
            "category": cls.category,
            "description": cls.description,
            "ntd_refs": cls.ntd_refs,
            "capability": cls.capability,
            "needs_model": cls.needs_model,
        })
    return out


def run_plugins(ctx: PluginContext,
                only: list[str] | None = None) -> list[CheckResult]:
    """Запускает плагины и возвращает результаты в виде обычных CheckResult.

    only — список кодов, которые нужно выполнить (None = все).
    """
    results: list[CheckResult] = []
    for cls in ALL_PLUGINS:
        if only and cls.code not in only:
            continue
        plugin = cls()
        try:
            available, reason = plugin.availability(ctx)
        except Exception as e:
            results.append(plugin._not_performed(
                reason=f"Плагин {cls.code}: проверка доступности завершилась ошибкой "
                       f"{type(e).__name__}: {e}",
                detail="Плагин не запускался.",
            ))
            continue

        if not available:
            results.append(plugin._not_performed(
                reason=reason or f"плагин {cls.code} недоступен по неустановленной причине",
                detail=plugin.description,
            ))
            continue

        try:
            results.append(plugin.run(ctx))
        except Exception as e:
            # Ошибка внутри плагина не должна ронять всю проверку проекта.
            results.append(plugin._not_performed(
                reason=f"Плагин {cls.code} завершился ошибкой {type(e).__name__}: {e}",
                detail="Результат по этому плагину не получен.",
            ))
    return results


__all__ = [
    "AIPlugin", "PluginContext", "CAP_TEXT", "CAP_VISION",
    "ALL_PLUGINS", "list_plugins", "run_plugins",
    "LlmDocumentChecker", "CadStructureChecker", "DwgVisionChecker",
]