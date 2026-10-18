"""Проверка питания пожарных систем от двух источников (СП 6.13130.2021)."""
from checkers.base import Checker, CheckResult


def _rows(x):
    if not x:
        return []
    return x if isinstance(x, list) else x.get("rows", []) or []


class FirePowerDualChecker(Checker):
    code = "FIRE_POWER_DUAL"
    name = "Проверка питания пожарных систем от двух источников (СП 6.13130.2021)"
    category = "critical"
    ntd_refs = "СП 6.13130.2021; СП 76.13330.2016"

    def run(self, data):
        sources = data.get("power_sources")
        devices = _rows(data.get("fire_devices"))
        if not devices:
            return self._not_performed(
                reason="Нет данных о пожарных приборах/оповещателях.",
                detail="Нужна таблица с пожарными извещателями, оповещателями или приборами.",
            )
        src_rows = _rows(sources)
        if not src_rows:
            return self._not_performed(
                reason="Нет данных об источниках питания.",
                detail="Нужна таблица источников питания (источник, номинал по току, мощность).",
            )
        if len(src_rows) < 2:
            return self._fail(
                detail=(f"Требуется не менее двух источников питания по СП 6.13130.2021, "
                        f"в данных {len(src_rows)}."),
                evidence=[{"type": "sources", "count": len(src_rows)}],
            )
        return self._ok(
            detail=f"Источников питания: {len(src_rows)} — требуется дублирование.",
            evidence=[{"type": "sources", "count": len(src_rows)}],
        )