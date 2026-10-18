"""Проверка кабелей пожарной сигнализации по ГОСТ 31565-2012 / СП 6.13130.2021."""
from checkers.base import Checker, CheckResult


def _rows(x):
    if not x:
        return []
    return x if isinstance(x, list) else x.get("rows", []) or []


class FireAlarmCableChecker(Checker):
    code = "FIRE_ALARM_CABLE"
    name = "Проверка кабелей пожарной сигнализации по ГОСТ 31565-2012"
    category = "critical"
    ntd_refs = "ГОСТ 31565-2012; СП 6.13130.2021; СП 76.13330.2016"

    ALLOWED = ("ВВГнг", "ВВГнг-LS", "ВВГнг-LSLT", "КВВГнг", "КВВГнг-LS",
               "ВВГнг-П", "ВВГнг-LS-П", "НГВВГ", "ВБШв", "КПСЭv", "КПСЭv-П")

    def run(self, data):
        rows = _rows(data.get("fire_cable"))
        if not rows:
            return self._not_performed(
                reason="Нет данных о кабелях пожарной сигнализации.",
                detail="Нужна таблица (xls/xlsx или PDF) с кабелями пожарных систем: марка, сечение, прокладка.",
            )
        HEADER = ("марк", "тип", "наимен", "позиц", "кабель", "оборуд", "назв")
        bad = []
        checked = 0
        for r in rows:
            if not r:
                continue
            first = str(r[0]).strip().lower()
            if any(h in first for h in HEADER):
                continue
            brand = " ".join(first.upper().replace(" ", "").split())
            checked += 1
            if not any(brand.startswith(a.upper()) for a in self.ALLOWED):
                bad.append({"name": str(r[0]),
                            "issue": "марка не входит в перечень огнестойких кабелей"})
        if checked == 0:
            return self._not_performed(reason="Не удалось распарсить ни одной строки кабелей.")
        if not bad:
            return self._ok(
                detail=f"Проверено {checked} кабелей: все из перечня огнестойких марок.",
                evidence=[{"type": "checked", "count": checked}],
            )
        return self._fail(
            detail=f"Выявлено {len(bad)} отклонений из {checked} кабелей.",
            evidence=[{"type": "violations", "items": bad[:50]}],
        )