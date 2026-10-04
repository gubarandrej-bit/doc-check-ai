"""Проверка 4: Подбор аккумуляторов (Емкость по времени резервирования)."""
from checkers.base import Checker, CheckResult


class BatteryChecker(Checker):
    code = "BATTERY_SELECTION"
    name = "Проверка подбора аккумуляторов (емкость/напряжение под нагрузку)"
    ntd_refs = "ПУЭ п.п. 3.1.19-3.1.37; СП 6.13130.2021"

    def run(self, data):
        batteries = data.get("batteries")
        load = data.get("battery_load")
        if not batteries:
            return self._not_performed(
                reason="Нет данных об аккумуляторах (таблица «аккумуляторы»).",
                detail="Нужна таблица (xls/xlsx или PDF): ти��, напряжение, емкость Ач, время резервирования ч.",
            )
        rows = batteries if isinstance(batteries, list) else batteries.get("rows", [])
        if not rows:
            return self._not_performed(reason="Таблица аккумуляторов пуста.")

        load_A = 0.0
        if load:
            try:
                load_A = float(str(load[0]).replace(",", "."))
            except Exception:
                load_A = 0.0

        bad = []
        checked = 0
        for r in rows:
            if len(r) < 4:
                continue
            btype, v, cap, t = r[0], r[1], r[2], r[3]
            try:
                v = float(str(v).replace(",", "."))
                cap = float(str(cap).replace(",", "."))
                t = float(str(t).replace(",", "."))
            except Exception:
                continue
            checked += 1
            need = load_A * t  # Ач необходимо при заданном времени резервирования
            if load_A > 0 and cap < need:
                bad.append({
                    "battery": str(btype), "V": v, "capacity_Ah": cap,
                    "load_A": load_A, "reserve_h": t, "need_Ah": round(need, 1),
                    "issue": "емкость недостаточна для заданного времени резервирования",
                })
            if v not in (12, 24, 36, 48, 110, 220):
                bad.append({"battery": str(btype), "V": v, "issue": "подозрительное номинальное напряжение"})
        if checked == 0:
            return self._not_performed(reason="Не удалось распарсить аккумуляторы.")
        if not bad:
            return self._ok(
                detail=f"Проверено {checked} аккумуляторов. Нагрузка={load_A} А, емкость соответствует времени резервирования.",
                evidence=[{"type": "checked", "count": checked, "load_A": load_A}],
            )
        return self._fail(
            detail=f"Выявлено {len(bad)} отклонений из {checked} аккумуляторов.",
            evidence=[{"type": "violations", "items": bad[:50]}],
        )