"""Проверка 2: Подбор кабеля по марке и сечению согласно нагрузкам (ПУЭ, ГОСТ).

Справочные токи допустимых нагрузок — по ГОСТ 27570.1 / ПУЭ гл. 1.3 (для медных
кабелей с изоляцией из ПВХ, прокладка в воздухе, t=25C). Значения приблизительные,
для проверки логики; при необходимости уточняйте по актуальной редакции ГОСТ.
"""
from checkers.base import Checker, CheckResult

# марка -> {сечение мм2: ток А (справочно)}
AMPACITY = {
    "ВВГ":  {1.5: 22, 2.5: 27, 4: 38, 6: 46, 10: 60, 16: 78, 25: 101, 35: 124, 50: 160, 70: 198, 95: 238, 120: 284},
    "ВВГП": {1.5: 22, 2.5: 27, 4: 38, 6: 46, 10: 60, 16: 78, 25: 101, 35: 124, 50: 160, 70: 198, 95: 238, 120: 284},
    "NYM":   {1.5: 25, 2.5: 34, 4: 45, 6: 56, 10: 73, 16: 94, 25: 120, 35: 150, 50: 191, 70: 237, 95: 284},
    "КВВГ":  {1.5: 19, 2.5: 25, 4: 35, 6: 42, 10: 55, 16: 70, 25: 90, 35: 110, 50: 140, 70: 175, 95: 215, 120: 250},
    "АВВГ":  {1.5: 22, 2.5: 27, 4: 38, 6: 46, 10: 60, 16: 78, 25: 101, 35: 124, 50: 160, 70: 198, 95: 238, 120: 284},
}

SECTIONS = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120]


def _norm(s):
    return " ".join(str(s).upper().replace(" ", "").split())


class CableSelectionChecker(Checker):
    code = "CABLE_SELECTION"
    name = "Проверка подбора кабелей по марке и сечению согласно нагрузкам (ПУЭ, ГОСТ)"
    ntd_refs = "ПУЭ п.п. 1.3.10, 1.3.11; ГОСТ 27570.1; ГОСТ 31565-2012"

    def run(self, data):
        loads = data.get("cable_loads")
        if not loads:
            return self._not_performed(
                reason="Нет данных о нагрузках на кабели (таблица «нагрузки» в xls).",
                detail="Для проверки нужен xls с нагрузками: кабель/марка, сечение, ток нагрузки А.",
            )
        rows = loads if isinstance(loads, list) else loads.get("rows", [])
        if not rows:
            return self._not_performed(reason="Таблица нагрузок пуста.")

        bad = []
        checked = 0
        for r in rows:
            if len(r) < 3:
                continue
            brand, section, current = r[0], r[1], r[2]
            try:
                section = float(str(section).replace(",", "."))
                current = float(str(current).replace(",", "."))
            except Exception:
                continue
            b = _norm(brand)
            table = AMPACITY.get(b)
            if not table:
                bad.append({"name": str(brand), "issue": "марка не найдена в справочнике"})
                continue
            amp = table.get(section)
            if amp is None:
                bad.append({"name": f"{brand} {section}", "issue": "сечение отсутствует в справочнике"})
                continue
            checked += 1
            # ПУЭ: для постоянной нагрузки сечение подбирают с запасом >=1.25
            if amp < current * 1.25:
                bad.append({
                    "name": f"{brand} {section} мм2",
                    "load_A": current, "ampacity_A": amp,
                    "need_A": round(current * 1.25, 1),
                    "issue": "сечение недостаточно (Iдоп < Iрасч*1.25)",
                })
        if checked == 0:
            return self._not_performed(reason="Не удалось распарсить ни одной строки нагрузок.")
        if not bad:
            return self._ok(
                detail=f"Проверено {checked} кабелей: все соответствуют ПУЭ (I*c <= Iдоп).",
                evidence=[{"type": "checked", "count": checked}],
            )
        return self._fail(
            detail=f"Выявлено {len(bad)} отклонений из {checked} проверенных.",
            evidence=[{"type": "violations", "items": bad[:50]}],
        )