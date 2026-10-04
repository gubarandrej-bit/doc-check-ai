"""Проверка 6: Оборудование на схемах сверяется со спецификацией."""
from checkers.base import Checker, CheckResult


def _index(items):
    out = {}
    if not items:
        return out
    for r in items:
        if not r:
            continue
        name = str(r[0]).strip()
        if not name:
            continue
        key = " ".join(name.lower().split())
        out[key] = out.get(key, 0.0) + 1
    return out


class EquipmentSpecChecker(Checker):
    code = "EQUIPMENT_SPEC"
    name = "Сверка оборудования на схемах со спецификацией"
    ntd_refs = "ГОСТ 21.208-2013; ГОСТ Р 21.101-2026"

    def run(self, data):
        spec = data.get("spec")
        scheme_eq = data.get("scheme_equipment")
        if not spec:
            return self._not_performed(reason="Отсутствует спецификация (xls или таблица в PDF).")
        spec_rows = spec.get("sheets", {}) if isinstance(spec, dict) else {}
        # Ищем лист по подстроке, а не по точному имени: у PDF таблицы нет
        # имени листа, а у xls оно может быть «Спецификация оборудования»,
        # «equipment», «ТОВ». Точное совпадение работало только для двух
        # зашитых вариантов и молча пропускало проверку.
        spec_idx = _index(next((rows for name, rows in spec_rows.items()
                                if any(k in name.lower() for k in
                                       ("специф", "материал", "equipment", "тов"))), []))
        scheme_idx = _index(scheme_eq) if scheme_eq else {}

        if not spec_idx:
            return self._not_performed(
                reason="Не найдена таблица спецификации/материалов.",
                detail="Проверьте, что лист или таблица называется «спецификация», «материалы» или equipment и содержит столбец с наименованием.",
            )
        if not scheme_idx:
            return self._not_performed(
                reason="Нет данных об оборудовании, указанном на схемах.",
                detail="Загрузите таблицу с перечнем оборудования со схем или текстовое описание.",
            )

        only_spec = {k: v for k, v in spec_idx.items() if k not in scheme_idx}
        only_scheme = {k: v for k, v in scheme_idx.items() if k not in spec_idx}
        if not only_spec and not only_scheme:
            return self._ok(
                detail=f"Совпадение: {len(spec_idx)} позиций оборудования присутствуют и в спецификации, и на схемах.",
                evidence=[{"type": "match", "count": len(spec_idx)}],
            )
        msgs = []
        if only_spec:
            msgs.append(f"только в спецификации: {len(only_spec)} поз.")
        if only_scheme:
            msgs.append(f"только на схемах: {len(only_scheme)} поз.")
        return self._fail(
            detail="; ".join(msgs),
            evidence=[
                {"type": "only_spec", "items": list(only_spec)[:20]},
                {"type": "only_scheme", "items": list(only_scheme)[:20]},
            ],
        )