"""Проверка СКС (структурированные кабельные системы) по ГОСТ Р 53246-2025."""
from checkers.base import Checker, CheckResult


def _rows(x):
    if not x:
        return []
    return x if isinstance(x, list) else x.get("rows", []) or []


class ScsChecker(Checker):
    code = "SCS_CHECK"
    name = "Проверка СКС (структурированные кабельные системы)"
    category = "critical"
    ntd_refs = "ГОСТ Р 53246-2025; ГОСТ Р 21.703-2020"

    def run(self, data):
        net_rows = _rows(data.get("net_rows"))
        if not net_rows:
            return self._not_performed(
                reason="Нет данных о СКС (таблица с кабельными системами).",
                detail="Нужна таблица (xls/xlsx или PDF) с данными СКС: типы кабелей, длины линий.",
            )
        cable_rows = [r for r in net_rows if any(h in str(r[0]).lower()
                       for h in ("кабель", "витая пара", "оптоволокно"))]
        if not cable_rows:
            return self._not_performed(
                reason="В данных СКС не обнаружено информации о кабельных линиях.",
                detail="Проверьте наличие сведений о типах кабелей, их длинах и топологии.",
            )
        return self._ok(
            detail=f"Обнаружено {len(cable_rows)} записей о кабельных линиях СКС.",
            evidence=[{"type": "cables", "count": len(cable_rows)}],
        )