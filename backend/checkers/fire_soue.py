"""Проверка системы оповещения и управления эвакуацией (СП 3.13130.2009)."""
from checkers.base import Checker, CheckResult


def _rows(x):
    if not x:
        return []
    return x if isinstance(x, list) else x.get("rows", []) or []


class FireSoueChecker(Checker):
    code = "FIRE_SOUE"
    name = "Проверка системы оповещения и управления эвакуацией (СП 3.13130.2009)"
    category = "critical"
    ntd_refs = "СП 3.13130.2009; 123-ФЗ"

    def run(self, data):
        devices = _rows(data.get("fire_devices"))
        text = (data.get("doc_text") or "") + "\n" + (data.get("scheme_text") or "")
        if not devices and not text.strip():
            return self._not_performed(
                reason="Нет данных о СОУЭ — ни приборов, ни текстового описания.",
                detail="Нужна таблица с оповещателями/световыми указателями или описание путей.",
            )
        found = []
        if devices:
            found.append(f"приборов/оповещателей: {len(devices)}")
        low = text.lower()
        for kw in ("световой указатель", "светофор", "эвакуационн", "оповещ"):
            if kw in low:
                found.append(f"упоминание «{kw}» в тексте")
                break
        if not found:
            return self._not_performed(
                reason="В данных не найдено приборов СОУЭ и не упоминаются эвакуационные пути.",
                detail="Проверьте наличие оповещателей, световых указателей и описания путей.",
            )
        return self._ok(
            detail="Данные СОУЭ распознаны: " + "; ".join(found),
            evidence=[{"type": "devices", "count": len(devices)}],
        )