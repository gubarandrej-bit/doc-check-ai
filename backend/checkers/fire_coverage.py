"""Проверка полноты перечня защищаемого оборудования (СП 486.1311500.2020)."""
from checkers.base import Checker, CheckResult


def _rows(x):
    if not x:
        return []
    return x if isinstance(x, list) else x.get("rows", []) or []


def _find(rows, *keys):
    out = []
    for r in rows:
        if not r:
            continue
        cell = str(r[0]).lower()
        if any(k in cell for k in keys):
            out.append(r)
    return out


class FireEquipmentCoverageChecker(Checker):
    code = "FIRE_COVERAGE"
    name = "Проверка полноты перечня защищаемого оборудования (СП 486.1311500.2020)"
    category = "critical"
    ntd_refs = "СП 486.1311500.2020; 123-ФЗ"

    def run(self, data):
        eq = _rows(data.get("fire_equipment"))
        if not eq:
            return self._not_performed(
                reason="Нет перечня защищаемого оборудования (таблица с зонами/оборудованием).",
                detail="Нужна таблица (xls/xlsx или PDF) с перечнем зданий/помещений и оборудования.",
            )
        zones = _find(eq, "зона", "помещ", "здан", "секц")
        devices = _find(eq, "извещат", "датчик", "оповещ", "сирен", "светофор")
        if not zones and not devices:
            return self._not_performed(
                reason="В перечне не найдены ни зоны, ни приборы.",
                detail="Проверьте, что таблица содержит столбцы с зонами/помещениями и типами устройств.",
            )
        msgs = []
        if zones:
            msgs.append(f"зона/помещений: {len(zones)}")
        if devices:
            msgs.append(f" устройств: {len(devices)}")
        return self._ok(
            detail="Перечень распознан: " + "; ".join(msgs),
            evidence=[{"type": "zones", "count": len(zones)},
                      {"type": "devices", "count": len(devices)}],
        )