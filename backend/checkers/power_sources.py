"""Проверка 3: Расчеты источников питания по току и мощности (ПУЭ)."""
from checkers.base import Checker, CheckResult


class PowerSourcesChecker(Checker):
    code = "POWER_SOURCES"
    name = "Проверка расчетов источников питания по току и мощности"
    ntd_refs = "ПУЭ п.п. 3.1.19-3.1.37; СП 76.13330.2016"

    def run(self, data):
        sources = data.get("power_sources")
        loads = data.get("power_loads")
        if not sources:
            return self._not_performed(
                reason="Нет данных об источниках питания (таблица «источники питания»).",
                detail="Нужна таблица (xls/xlsx или PDF): источник, номинал по току А, мощность кВт, коэффициент нагрузки.",
            )
        rows = sources if isinstance(sources, list) else sources.get("rows", [])
        if not rows:
            return self._not_performed(reason="Таблица источников питания пуста.")

        total_load_A = 0.0
        total_load_kW = 0.0
        if loads:
            for r in (loads if isinstance(loads, list) else loads.get("rows", [])):
                try:
                    if len(r) >= 2:
                        total_load_A += float(str(r[0]).replace(",", "."))
                    if len(r) >= 3:
                        total_load_kW += float(str(r[1]).replace(",", "."))
                except Exception:
                    pass

        bad = []
        checked = 0
        for r in rows:
            if len(r) < 3:
                continue
            name, i_nom, p_nom = r[0], r[1], r[2]
            try:
                i_nom = float(str(i_nom).replace(",", "."))
                p_nom = float(str(p_nom).replace(",", "."))
            except Exception:
                continue
            checked += 1
            # коэффициент загрузки при суммарном токе нагрузки
            if total_load_A > 0:
                k = total_load_A / i_nom
                if k > 1.0:
                    bad.append({
                        "source": str(name), "I_nom_A": i_nom, "I_load_A": round(total_load_A, 1),
                        "k": round(k, 2), "issue": "перегрузка источника по току (k>1)",
                    })
                elif k > 0.85:
                    bad.append({
                        "source": str(name), "I_nom_A": i_nom, "I_load_A": round(total_load_A, 1),
                        "k": round(k, 2), "issue": "высокая загрузка (k>0.85), рекомендуется резерв",
                    })
            if total_load_kW > 0 and p_nom > 0 and total_load_kW > p_nom:
                bad.append({
                    "source": str(name), "P_nom_kW": p_nom, "P_load_kW": round(total_load_kW, 1),
                    "issue": "превышение мощности нагрузки",
                })
        if checked == 0:
            return self._not_performed(reason="Не удалось распарсить источники питания.")
        if not bad:
            return self._ok(
                detail=f"Проверено {checked} источников. Суммарный ток нагрузки={round(total_load_A,1)} А, мощность={round(total_load_kW,1)} кВт — в пределах номиналов.",
                evidence=[{"type": "checked", "count": checked, "load_A": total_load_A, "load_kW": total_load_kW}],
            )
        return self._fail(
            detail=f"Выявлено {len(bad)} отклонений из {checked} источников.",
            evidence=[{"type": "violations", "items": bad[:50]}],
        )