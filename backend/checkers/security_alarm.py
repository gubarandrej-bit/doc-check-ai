"""Проверка охранной сигнализации по ГОСТ Р 58238-2018."""
from checkers.base import Checker, CheckResult


def _rows(x):
    if not x:
        return []
    return x if isinstance(x, list) else x.get("rows", []) or []


class SecurityAlarmChecker(Checker):
    code = "SECURITY_ALARM_CHECK"
    name = "Проверка охранной сигнализации"
    category = "critical"
    ntd_refs = "ГОСТ Р 58238-2018; ГОСТ Р 21.703-2020"

    def run(self, data):
        net_rows = _rows(data.get("net_rows"))
        if not net_rows:
            return self._not_performed(
                reason="Нет данных об охранной сигнализации (таблица с датчиками).",
                detail="Нужна таблица (xls/xlsx или PDF) с данными охранной сигнализации.",
            )
        alarm_rows = [r for r in net_rows if any(h in str(r[0]).lower()
                      for h in ("охран", "сигна", "датчик", "извещ", "пкп", "панель"))]
        if not alarm_rows:
            return self._not_performed(
                reason="В данных не обнаружено информации об охранной сигнализации.",
                detail="Проверьте наличие сведений о датчиках и панелях управления.",
            )
        return self._ok(
            detail=f"Обнаружено {len(alarm_rows)} записей об оборудовании охранной сигнализации.",
            evidence=[{"type": "alarm_equipment", "count": len(alarm_rows)}],
        )