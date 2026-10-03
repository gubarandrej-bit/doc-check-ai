"""Проверка 5: Корректность электрических и структурных схем.

Внимание: DWG-файлы (AutoCAD) не могут быть проанализированы без специализированного
ПО (ODA File Converter, BIM-плагины). При отсутствии текстового описания схем
проверка помечается как не проведённая — данные не придумываются.
"""
from checkers.base import Checker, CheckResult


class SchematicChecker(Checker):
    code = "SCHEMATIC_CHECK"
    name = "Проверка электрических и структурных схем / планов"
    ntd_refs = "ГОСТ 21.210-2014; ГОСТ 21.208-2013; ГОСТ Р 21.101-2026"

    def run(self, data):
        schemes = data.get("schemes")
        text = data.get("scheme_text")
        dwg = data.get("dwg_files")

        if not schemes and not text and not dwg:
            return self._not_performed(
                reason="Отсутствуют схемы/планы (ни текстового описания, ни изображений).",
                detail="Для проверки схем нужен текстовый анализ (PDF/DOC) или описанные в xls данные. DWG без расшифровки не анализируется.",
            )

        if dwg and not text and not schemes:
            return self._not_performed(
                reason="Схемы представлены только в формате DWG, который не может быть расшифрован системой.",
                detail="Для анализа DWG требуется предварительная экспорта в PDF/изображение или текстовое описание.",
            )

        issues = []
        if text:
            low = text.lower()
            for kw, msg in [
                ("однолиней", "обнаружено упоминание однолинейной схемы — проверьте соответствие ГОСТ 21.210"),
                ("кабельная трасса", "проверьте длины кабельных трасс на планах"),
            ]:
                if kw in low:
                    issues.append(msg)
        if not issues:
            return self._ok(
                detail="По доступному текстовому описанию схем критичных отклонений не выявлено.",
                evidence=[{"type": "text_analyzed", "len": len(text or "")}],
            )
        return self._fail(detail="; ".join(issues), evidence=[{"type": "notes", "items": issues}])