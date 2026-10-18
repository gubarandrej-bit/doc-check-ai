"""Проверка СКУД (система контроля и управления доступом) по ГОСТ Р 58238-2018."""
from checkers.base import Checker, CheckResult


def _rows(x):
    if not x:
        return []
    return x if isinstance(x, list) else x.get("rows", []) or []


class SkudChecker(Checker):
    code = "SKUD_CHECK"
    name = "Проверка СКУД (контроль доступа)"
    category = "critical"
    ntd_refs = "ГОСТ Р 58238-2018; ГОСТ Р 21.703-2020"

    def run(self, data):
        net_rows = _rows(data.get("net_rows"))
        if not net_rows:
            return self._not_performed(
                reason="Нет данных о СКУД (таблица с оборудованием контроля доступа).",
                detail="Нужна таблица (xls/xlsx или PDF) с данными СКУД: считыватели, контроллеры, замки.",
            )
        skud_rows = [r for r in net_rows if any(h in str(r[0]).lower()
                     for h in ("скуд", "доступ", "двери", "замок", "счит", "контроллер"))]
        if not skud_rows:
            return self._not_performed(
                reason="В данных не обнаружено информации об оборудовании СКУД.",
                detail="Проверьте наличие сведений о считывателях и контроллерах доступа.",
            )
        return self._ok(
            detail=f"Обнаружено {len(skud_rows)} записей об оборудовании СКУД.",
            evidence=[{"type": "skud_equipment", "count": len(skud_rows)}],
        )