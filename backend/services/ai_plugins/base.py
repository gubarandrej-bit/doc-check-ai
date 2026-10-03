"""Базовый класс для плагинов ИИ-анализа.

Плагин наследует Checker — это не случайно. Так переиспользуется весь механизм
честности: результат имеет статус passed | failed | not_performed, и если исходных
данных или возможностей не хватает, плагин обязан вернуть not_performed с причиной,
а не выдумать вывод.
"""
from dataclasses import dataclass, field
from typing import Any

from checkers.base import Checker, CheckResult


# Требуемые возможности модели.
CAP_TEXT = "text"      # понимание текста (все LLM)
CAP_VISION = "vision"  # работа с изображениями (нужна vision-модель)


@dataclass
class PluginContext:
    """Всё, что плагину нужно для работы. Ничего не выдумывается — только то, что реально есть."""

    data: dict[str, Any] = field(default_factory=dict)   # данные, собранные из файлов
    model: Any = None                                     # выбранная модель ИИ (ORM AiModel)
    ntd_refs: list[dict] = field(default_factory=list)    # актуальные НТД (номер, название, статус)
    mode: str = "local"                                   # local | cloud | hybrid

    # --- удобные доступы с честной проверкой наличия ---

    def model_has(self, capability: str) -> bool:
        """Проверяет, заявлена ли у модели нужная способность."""
        if self.model is None:
            return False
        caps = model_capabilities(self.model)
        return capability in caps

    @property
    def doc_text(self) -> str:
        return (self.data.get("doc_text") or "").strip()

    @property
    def dwg_paths(self) -> list[str]:
        return self.data.get("dwg_paths") or []


def model_capabilities(model: Any) -> set[str]:
    """Определяет возможности модели.

    Способность vision определяется по явной пометке в БД или по имени модели,
    если модели известны как мультимодальные. Если определить нельзя — считается,
    что есть только text. Лучше не выдать лишнего, чем придумать возможность.
    """
    if model is None:
        return set()

    raw = (getattr(model, "capabilities", "") or "").strip().lower()
    if raw:
        return {c.strip() for c in raw.replace(",", " ").split() if c.strip()}

    # Известные мультимодальные модели, если пометки в БД нет.
    mid = (getattr(model, "model_id", "") or "").lower()
    vision_hints = (
        "vision", "llava", "bakllava", "moondream", "minicpm-v", "qwen-vl",
        "qwen2-vl", "qwen2.5-vl", "llama-3.2-vision", "pixtral", "internvl",
        "gemma-3", "gpt-4o", "gpt-4.1", "gpt-5", "claude-3", "claude-4", "gemini",
    )
    caps = {CAP_TEXT}
    if any(h in mid for h in vision_hints):
        caps.add(CAP_VISION)
    return caps


class AIPlugin(Checker):
    """Плагин ИИ-анализа.

    Наследует Checker: доступны _ok / _fail / _not_performed.

    Порядок работы плагина:
      1. availability() — можно ли вообще запустить плагин;
      2. run() — сам анализ.
    Если availability() вернула (False, причина) — вызывающий код записывает
    not_performed с этой причиной, и run() не вызывается вовсе.
    """

    code: str = "AI_PLUGIN"
    name: str = "Плагин ИИ-анализа"
    category: str = "non-critical"
    ntd_refs: str = ""
    description: str = ""
    capability: str = CAP_TEXT  # какая способность модели нужна
    needs_model: bool = True    # False — плагину модель ИИ не требуется вовсе

    def availability(self, ctx: PluginContext) -> tuple[bool, str]:
        """(доступен ли плагин, причина недоступности)."""
        if not self.needs_model:
            return True, ""
        if ctx.model is None:
            return False, "Модель ИИ не выбрана — плагин не запускался."
        if not getattr(ctx.model, "is_active", True):
            return False, f"Модель «{getattr(ctx.model, 'name', '?')}» отключена."
        if not ctx.model_has(self.capability):
            if self.capability == CAP_VISION:
                return False, (
                    f"Выбранная модель «{getattr(ctx.model, 'name', '?')}» не заявлена как "
                    "мультимодальная (vision). Укажите способность vision в настройках модели "
                    "или выберите другую модель — распознавание изображений чертежей не выполнялось."
                )
            return False, (
                f"У модели «{getattr(ctx.model, 'name', '?')}» не заявлена способность "
                "text (обработка текста)."
            )
        return True, ""

    def run(self, ctx: PluginContext) -> CheckResult:  # pragma: no cover - абстрактный
        raise NotImplementedError