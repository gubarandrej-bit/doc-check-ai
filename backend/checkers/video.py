"""Проверка системы видеонаблюдения по ГОСТ Р 58238-2018."""
from checkers.base import Checker, CheckResult


def _rows(x):
    if not x:
        return []
    return x if isinstance(x, list) else x.get("rows", []) or []


class VideoSurveillanceChecker(Checker):
    code = "VIDEO_SURVEILLANCE_CHECK"
    name = "Проверка системы видеонаблюдения"
    category = "critical"
    ntd_refs = "ГОСТ Р 58238-2018; ГОСТ Р 21.703-2020"

    def run(self, data):
        net_rows = _rows(data.get("net_rows"))
        if not net_rows:
            return self._not_performed(
                reason="Нет данных о видеонаблюдении (таблица с камерами).",
                detail="Нужна таблица (xls/xlsx или PDF) с данными видеонаблюдения.",
            )
        video_rows = [r for r in net_rows if any(h in str(r[0]).lower()
                      for h in ("камера", "вид", "видео", "наблюд"))]
        if not video_rows:
            return self._not_performed(
                reason="В данных не обнаружено информации о видеокамерах.",
                detail="Проверьте наличие сведений о видеокамерах и их характеристиках.",
            )
        return self._ok(
            detail=f"Обнаружено {len(video_rows)} записей об оборудовании видеонаблюдения.",
            evidence=[{"type": "video_equipment", "count": len(video_rows)}],
        )