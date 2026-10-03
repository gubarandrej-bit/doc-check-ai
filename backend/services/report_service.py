"""Генерация отчётов и ведомостей в форматах docx и xlsx."""
import datetime
from typing import Any

from config import REPORT_DIR


def _now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def _split(items):
    crit = [i for i in items if i.get("category") == "critical"]
    non = [i for i in items if i.get("category") != "critical"]
    return crit, non


def generate_docx(report_id: int, project_name: str, items: list[dict], summary: str) -> str:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()
    title = doc.add_heading("ОТЧЁТ о проверке проектной/рабочей документации", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p = doc.add_paragraph()
    p.add_run("Проект: ").bold = True
    p.add_run(project_name or "(не указан)")
    p = doc.add_paragraph()
    p.add_run("Дата проверки: ").bold = True
    p.add_run(_now_str())
    p = doc.add_paragraph()
    p.add_run("Идентификатор проверки: ").bold = True
    p.add_run(str(report_id))

    doc.add_heading("Выводы", level=1)
    doc.add_paragraph(summary or "—")

    crit, non = _split(items)
    doc.add_heading(f"Критические замечания ({len(crit)})", level=1)
    _fill_items(doc, crit)
    doc.add_heading(f"Некритические замечания ({len(non)})", level=1)
    _fill_items(doc, non)

    doc.add_heading("Перечень проверок", level=1)
    for it in items:
        h = doc.add_paragraph()
        h.add_run(f"[{it.get('status', '').upper()}] {it.get('name', '')} ({it.get('code', '')})").bold = True
        if it.get("reason_skipped"):
            r = doc.add_paragraph()
            r.add_run("Причина непроведения: ").italic = True
            r.add_run(it["reason_skipped"])
        if it.get("detail"):
            doc.add_paragraph(it["detail"])
        if it.get("ntd_refs"):
            r = doc.add_paragraph()
            r.add_run("НТД: ").bold = True
            r.add_run(it["ntd_refs"])

    path = REPORT_DIR / f"report_{report_id}.docx"
    doc.save(str(path))
    return str(path)


def _fill_items(doc, items):
    if not items:
        doc.add_paragraph("нет замечаний")
        return
    for it in items:
        t = doc.add_paragraph()
        t.add_run(f"• {it.get('name', '')} [{it.get('code', '')}]: ").bold = True
        t.add_run(it.get("detail", ""))
        if it.get("ntd_refs"):
            r = doc.add_paragraph()
            r.add_run("   НТД: " + it["ntd_refs"])


def generate_xls(report_id: int, project_name: str, items: list[dict], summary: str,
                 acts: dict | None = None) -> str:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Отчёт"

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1F2937")

    ws["A1"] = "ОТЧЁТ о проверке документации"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f"Проект: {project_name or '(не указан)'}"
    ws["A3"] = f"Дата: {_now_str()}"
    ws["A4"] = f"ID проверки: {report_id}"

    ws.append([])
    headers = ["Код", "Проверка", "Категория", "Статус", "Детали", "НТД", "Причина непроведения"]
    ws.append(headers)
    for c in ws[ws.max_row]:
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal="center")

    status_map = {"passed": "пройдена", "failed": "нарушение", "not_performed": "не проведена"}
    for it in items:
        ws.append([
            it.get("code", ""),
            it.get("name", ""),
            it.get("category", ""),
            status_map.get(it.get("status", ""), it.get("status", "")),
            it.get("detail", ""),
            it.get("ntd_refs", ""),
            it.get("reason_skipped", ""),
        ])

    # Ведомость объёмов работ
    ws2 = wb.create_sheet("Ведомость объемов работ")
    ws2.append(["№", "Наименование проверки", "Статус", "Категория", "Замечания"])
    for i, it in enumerate(items, 1):
        ws2.append([
            i, it.get("name", ""),
            status_map.get(it.get("status", ""), it.get("status", "")),
            it.get("category", ""),
            "да" if it.get("status") == "failed" else "нет",
        ])

    # Ведомость оборудования и материалов — из спецификации
    ws3 = wb.create_sheet("Ведомость оборудования")
    ws3.append(["№", "Наименование", "Количество", "Ед.", "Примечание"])
    spec = (acts or {}).get("spec_rows") or []
    for i, r in enumerate(spec, 1):
        ws3.append([i] + [str(c) for c in r[:4]])

    for sheet in (ws, ws2, ws3):
        for col in sheet.columns:
            width = max(len(str(c.value)) if c.value is not None else 0 for c in col)
            sheet.column_dimensions[col[0].column_letter].width = min(max(width + 2, 10), 60)

    path = REPORT_DIR / f"report_{report_id}.xlsx"
    wb.save(str(path))
    return str(path)