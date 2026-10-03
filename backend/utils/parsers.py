"""Парсинг загруженных файлов в структурированные данные.

Важно: при отсутствии данных НИЧЕГО не придумывается.
Если формат не поддерживается или данные не извлекаются — возвращается None
и проверка помечается как не проведённая с указанием причины.
"""
import os


def detect_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    if ext in ("xls", "xlsx"):
        return "xls"
    if ext in ("doc", "docx"):
        return "doc"
    if ext == "pdf":
        return "pdf"
    if ext == "dwg":
        return "dwg"
    return ext or "unknown"


def parse_xls(path: str) -> dict | None:
    """Возвращает {'sheets': {name: [rows]} } или None."""
    try:
        import openpyxl
    except Exception:
        return None
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
        out = {}
        for ws in wb.worksheets:
            rows = []
            for row in ws.iter_rows(values_only=True):
                if any(c is not None for c in row):
                    rows.append([("" if c is None else str(c)) for c in row])
            out[ws.title] = rows
        return {"sheets": out} if out else None
    except Exception:
        return None


def parse_doc(path: str) -> dict | None:
    """Возвращает {'text': ..., 'tables': ...} или None."""
    try:
        import docx
    except Exception:
        return None
    try:
        d = docx.Document(path)
        paragraphs = [p.text for p in d.paragraphs if p.text.strip()]
        tables = []
        for t in d.tables:
            tables.append([[c.text for c in r.cells] for r in t.rows])
        return {"text": "\n".join(paragraphs), "tables": tables} if (paragraphs or tables) else None
    except Exception:
        return None


def parse_pdf(path: str) -> dict | None:
    """Текстовое извлечение. Сканированные PDF без текстового слоя вернут None."""
    try:
        from pypdf import PdfReader
    except Exception:
        return None
    try:
        reader = PdfReader(path)
        text = "\n".join((pg.extract_text() or "") for pg in reader.pages)
        return {"text": text, "pages": len(reader.pages)} if text.strip() else None
    except Exception:
        return None


def parse_file(path: str, ftype: str) -> dict | None:
    if ftype == "xls":
        return parse_xls(path)
    if ftype == "doc":
        return parse_doc(path)
    if ftype == "pdf":
        return parse_pdf(path)
    if ftype == "dwg":
        # DWG-файлы не могут быть расшифрованы без специализированного
        # ПО (например, ODA File Converter). Данные не извлекаются.
        return None
    return None