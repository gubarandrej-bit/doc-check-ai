"""Проверка 1: Сверка кабельного журнала со спецификацией (наименования и количество).

НТД: ГОСТ Р 21.703-2020, ГОСТ 21.208-2013, СП 76.13330.2016.
"""
from checkers.base import Checker, CheckResult


def _find_sheet(data, candidates):
    sheets = (data or {}).get("sheets") or {}
    for c in candidates:
        for name, rows in sheets.items():
            if c.lower() in name.lower():
                return name, rows
    return None, None


def _index_rows(rows):
    """Собирает словарь: ключ (нормализованное наименование) -> суммарное количество."""
    out = {}
    if not rows:
        return out
    header = [str(c).strip().lower() for c in rows[0]]
    def col(*keys):
        for i, h in enumerate(header):
            if any(k in h for k in keys):
                return i
        return None
    ni = col("наимен", "наименование", "кабель", "позиция", "тов", "артикул")
    qi = col("кол", "quantity", "шт", "м", "примеч")
    for r in rows[1:]:
        if not r or all(c in (None, "") for c in r):
            continue
        name = str(r[ni]).strip() if ni is not None and ni < len(r) else ""
        if not name:
            continue
        qty = 0.0
        if qi is not None and qi < len(r) and r[qi] not in (None, ""):
            try:
                qty = float(str(r[qi]).replace(",", "."))
            except Exception:
                qty = 0.0
        key = " ".join(name.lower().split())
        out[key] = out.get(key, 0.0) + qty
    return out


class CableJournalSpecChecker(Checker):
    code = "CABLE_JOURNAL_SPEC"
    name = "Сверка кабельного журнала со спецификацией по наименованиям и количеству"
    ntd_refs = "ГОСТ Р 21.703-2020; ГОСТ 21.208-2013; СП 76.13330.2016"

    def run(self, data):
        spec = data.get("spec")
        journal = data.get("cable_journal")
        if not spec or not journal:
            missing = []
            if not spec:
                missing.append("спецификация")
            if not journal:
                missing.append("кабельный журнал")
            return self._not_performed(
                reason="Отсутствуют исходные данные: " + ", ".join(missing),
                detail="Нужны обе таблицы (xls/xlsx или таблицы в PDF) с наименованиями и количеством.",
            )

        spec_rows = _find_sheet(spec, ["специф", "материал", "equipment", "тов"])
        jour_rows = _find_sheet(journal, ["кабель", "журнал", "список", "tray"])

        spec_idx = _index_rows(spec_rows[1]) if spec_rows else {}
        jour_idx = _index_rows(jour_rows[1]) if jour_rows else {}

        if not spec_idx or not jour_idx:
            return self._not_performed(
                reason="Не удалось распознать структуру таблиц (столбцы «наименование»/«количество»).",
                detail="Проверьте, что в таблице есть заголовки: наименование/позиция и количество.",
            )

        only_spec = {k: v for k, v in spec_idx.items() if k not in jour_idx}
        only_jour = {k: v for k, v in jour_idx.items() if k not in spec_idx}
        mismatches = []
        for k, v in spec_idx.items():
            if k in jour_idx and abs(jour_idx[k] - v) > 1e-6:
                mismatches.append((k, v, jour_idx[k]))

        if not only_spec and not only_jour and not mismatches:
            return self._ok(
                detail=f"Совпадение: {len(spec_idx)} наименований, расхождений по количеству нет.",
                evidence=[{"type": "match", "count": len(spec_idx)}],
            )

        msgs = []
        if only_spec:
            msgs.append(f"только в спецификации: {len(only_spec)} поз. ({', '.join(list(only_spec)[:3])})")
        if only_jour:
            msgs.append(f"только в КЖ: {len(only_jour)} поз. ({', '.join(list(only_jour)[:3])})")
        if mismatches:
            msgs.append(f"расхождение по количеству: {len(mismatches)} поз.")
        return self._fail(
            detail="; ".join(msgs),
            evidence=[
                {"type": "only_spec", "items": list(only_spec)[:20]},
                {"type": "only_journal", "items": list(only_jour)[:20]},
                {"type": "qty_mismatch", "items": [{"name": k, "spec": a, "journal": b} for k, a, b in mismatches[:20]]},
            ],
        )