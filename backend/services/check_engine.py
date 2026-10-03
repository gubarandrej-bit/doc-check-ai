"""Движок проверок: собирает данные из загруженных файлов и запускает проверки.

Движок состоит из двух частей:
  1. Детерминированные проверки (checkers) — расчёты по ПУЭ, сверки таблиц.
  2. Плагины ИИ (ai_plugins) — анализ текста и чертжей выбранной моделью.

Плагины ИИ всегда возвращают запись в результатах: либо замечания, либо
not_performed с причиной. Молчаливого пропуска не бывает.
"""
import os
from typing import Any

from checkers.base import CheckResult
from checkers import (
    cable_journal, cable_selection, power_sources, batteries,
    schematics, spec_crosscheck,
)
from utils.parsers import parse_file, detect_type

CHECKER_CLASSES = [
    cable_journal.CableJournalSpecChecker,
    cable_selection.CableSelectionChecker,
    power_sources.PowerSourcesChecker,
    batteries.BatteryChecker,
    schematics.SchematicChecker,
    spec_crosscheck.EquipmentSpecChecker,
]

DRAWING_TYPES = {"dwg", "dxf"}


def _gather_data(files: list[dict]) -> dict[str, Any]:
    """Извлекает данные из списка загруженных файлов по типу."""
    data: dict[str, Any] = {"dwg_files": [], "drawing_paths": []}
    spec = journal = loads = sources = batteries = None
    scheme_text = ""
    doc_text = ""
    scheme_equipment = []
    for f in files:
        path = f.get("stored_path")
        ftype = f.get("file_type") or detect_type(f.get("filename", ""))
        if not path or not os.path.exists(path):
            continue

        # Чертежи передаём плагинам путями на диске, а не только именами:
        # конвертация DWG и разбор DXF требуют реального доступа к файлу.
        if ftype in DRAWING_TYPES:
            data["drawing_paths"].append(path)
            if ftype == "dwg":
                data["dwg_files"].append(f.get("filename"))
            continue

        parsed = parse_file(path, ftype)
        if not parsed:
            continue
        sheets = parsed.get("sheets") if isinstance(parsed, dict) else None
        if sheets:
            lowered = {k.lower(): v for k, v in sheets.items()}

            def pick(*keys):
                for k, v in lowered.items():
                    if any(x in k for x in keys):
                        return v
                return None

            if any("специф" in k or "материал" in k or "equipment" in k for k in lowered):
                spec = parsed
            if any("кабель" in k or "журнал" in k for k in lowered):
                journal = parsed
            if any("нагруз" in k for k in lowered):
                loads = pick("нагруз")
            if any("источник" in k or "ип" in k for k in lowered):
                sources = pick("источник") or pick("ип")
            if any("аккумулятор" in k or "батаре" in k for k in lowered):
                batteries = pick("аккумулятор") or pick("батаре")
            if any("оборуд" in k for k in lowered):
                scheme_equipment = pick("оборуд") or []
        text = parsed.get("text") if isinstance(parsed, dict) else None
        if text:
            scheme_text += "\n" + text
            # Весь текст документации уходит плагину ИИ: пояснительные записки,
            # спецификации и разделы стадии Р.
            doc_text += "\n" + text
    data.update(spec=spec, cable_journal=journal, cable_loads=loads,
                power_sources=sources, batteries=batteries,
                scheme_text=scheme_text, doc_text=doc_text,
                scheme_equipment=scheme_equipment)
    return data


def run_checks(files: list[dict], model=None,
               ntd_refs: list[dict] | None = None,
               mode: str = "local") -> list[CheckResult]:
    """Полный запуск проверок проекта.

    model — выбранная модель ИИ (или None). ntd_refs — перечень НТД для плагинов.
    """
    from services.ai_plugins import PluginContext, run_plugins

    data = _gather_data(files)

    results: list[CheckResult] = []
    for checker_cls in CHECKER_CLASSES:
        results.append(checker_cls().run(data))

    ctx = PluginContext(data=data, model=model,
                        ntd_refs=ntd_refs or [], mode=mode)
    results.extend(run_plugins(ctx))

    return results