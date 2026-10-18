"""Проверка АСУ/АСУТП (автоматизированные системы управления) по ГОСТ 21.208-2013."""
from checkers.base import Checker, CheckResult


def _rows(x):
    if not x:
        return []
    return x if isinstance(x, list) else x.get("rows", []) or []


class AsuAsutpChecker(Checker):
    code = "ASU_ASUTP_CHECK"
    name = "Проверка АСУ/АСУТП (автоматизированные системы управления)"
    category = "critical"
    ntd_refs = "ГОСТ 21.208-2013; ГОСТ Р 21.101-2026; ГОСТ Р 21.703-2020"

    def run(self, data):
        net_rows = _rows(data.get("net_rows"))
        if not net_rows:
            return self._not_performed(
                reason="Нет данных об АСУ/АСУТП (таблица с оборудованием автоматизации).",
                detail="Нужна таблица (xls/xlsx или PDF) с данными АСУ/АСУТП: контроллеры, датчики.",
            )
        asu_rows = [r for r in net_rows if any(h in str(r[0]).lower()
                    for h in ("асу", "автомат", "регул", "контроллер", "датчик", "исполнит"))]
        if not asu_rows:
            return self._not_performed(
                reason="В данных не обнаружено информации об АСУ/АСУТП.",
                detail="Проверьте наличие сведений о ПЛК, датчиках, исполнительных механизмах.",
            )
        return self._ok(
            detail=f"Обнаружено {len(asu_rows)} записей об оборудовании АСУ/АСУТП.",
            evidence=[{"type": "asu_equipment", "count": len(asu_rows)}],
        )