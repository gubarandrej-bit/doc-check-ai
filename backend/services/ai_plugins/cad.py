"""Извлечение данных из инженерных чертежей (DWG / DXF).

Формат DWG — закрытый бинарный формат CAD. Читать его нативно в Python нельзя.
Рабочий конвейер такой:

    DWG --(ODA File Converter)--> DXF --(ezdxf)--> структурные данные
                                    \--(matplotlib)--> PNG --(vision-модель)--> описание

Что извлекается из DXF без всякого ИИ (это работает всегда, если есть ezdxf):
  - слои и их содержимое;
  - текстовые надписи (TEXT/MTEXT) — маркировки кабелей, оборудования, помещений;
  - вставки блоков (INSERT) — по сути, символы на схеме;
  - атрибуты блоков — номиналы, марки;
  - геометрия (линии, полилинии) и их длины;
  - размерные надписи.

Честные ограничения:
  - ODA File Converter — сторонняя программа, распространяемая Open Design Alliance.
    Её нельзя положить в репозиторий. Если она не установлена, конвертация невозможна
    и проверка помечается как не проведённая с указанием причины.
  - Понимание того, ЧТО нарисовано на чертеже (схема электрическая, план, спецификация),
    требует vision-модели. Без неё доступна только структурная информация.
"""
import glob
import os
import shutil
import subprocess
import tempfile

# Куда искать конвертер. Можно переопределить переменной окружения.
DEFAULT_ODA_PATHS = [
    "/opt/ODAFileConverter/ODAFileConverter",
    "/usr/bin/ODAFileConverter",
    "/usr/local/bin/ODAFileConverter",
    "C:\\Program Files\\ODAFileConverter\\ODAFileConverter.exe",
    "/Applications/ODAFileConverter/ODAFileConverter",
]


def oda_path() -> str | None:
    """Возвращает путь к ODA File Converter или None."""
    custom = (os.environ.get("ODA_CONVERTER_PATH") or "").strip()
    if custom and os.path.exists(custom):
        return custom
    for p in DEFAULT_ODA_PATHS:
        if os.path.exists(p):
            return p
    found = shutil.which("ODAFileConverter")
    return found


def oda_available() -> tuple[bool, str]:
    """(доступен ли конвертер, пояснение)."""
    p = oda_path()
    if p:
        return True, p
    return False, (
        "ODA File Converter не найден. Это сторонняя программа Open Design Alliance, "
        "она не распространяется вместе с DocCheck и не может быть установлена "
        "из репозитория. Скачайте её с https://www.opendesign.com/guestfiles/oda_file_converter "
        "и укажите путь в переменной окружения ODA_CONVERTER_PATH, "
        "либо экспортируйте чертежи в DXF или PDF вручную."
    )


def convert_dwg_to_dxf(dwg_path: str, outdir: str | None = None) -> tuple[str | None, str]:
    """Конвертирует DWG в DXF через ODA File Converter.

    Возвращает (путь_к_dxf, описание_ошибки). Если конвертация не удалась —
    путь None, а описание объясняет причину.
    """
    ok, detail = oda_available()
    if not ok:
        return None, detail
    exe = detail

    tmp = outdir or tempfile.mkdtemp(prefix="doccheck_dxf_")
    os.makedirs(tmp, exist_ok=True)
    in_dir = tempfile.mkdtemp(prefix="doccheck_dwg_")
    try:
        src = os.path.join(in_dir, os.path.basename(dwg_path))
        shutil.copy2(dwg_path, src)
        before = set(glob.glob(os.path.join(tmp, "*")))
        # ODAFileConverter <in> <out> <версия> <тип> <рекурсия> <аудит> [фильтр]
        proc = subprocess.run(
            [exe, in_dir, tmp, "ACAD2018", "DXF", "0", "1", "*.DWG"],
            capture_output=True, text=True, timeout=300,
        )
        produced = [p for p in set(glob.glob(os.path.join(tmp, "*"))) - before
                    if p.lower().endswith(".dxf")]
        if not produced:
            err = (proc.stderr or proc.stdout or "").strip()[:500]
            return None, f"ODA File Converter не создал DXF (код {proc.returncode}). {err}"
        return produced[0], ""
    except subprocess.TimeoutExpired:
        return None, "ODA File Converter не ответил за 300 секунд — конвертация прервана."
    except Exception as e:
        return None, f"ошибка запуска ODA File Converter: {type(e).__name__}: {e}"
    finally:
        shutil.rmtree(in_dir, ignore_errors=True)


def _text_of(entity) -> str:
    """Достаёт читаемый текст из TEXT/MTEXT/ATTRIB."""
    try:
        if entity.dxftype() == "MTEXT":
            try:
                return entity.plain_text()
            except Exception:
                return entity.text or ""
        return entity.dxf.text or ""
    except Exception:
        return ""


def extract_dxf_structure(dxf_path: str, max_texts: int = 1500) -> dict | None:
    """Извлекает структуру чертежа из DXF.

    Возвращает словарь с описанием либо None, если разобрать не удалось.
    """
    try:
        import ezdxf
    except Exception:
        return None

    try:
        doc = ezdxf.readfile(dxf_path)
    except Exception:
        return None

    try:
        msp = doc.modelspace()
    except Exception:
        return None

    out: dict = {
        "dxf_version": getattr(doc, "dxfversion", "") or getattr(doc, "acad_release", ""),
        "units": "",
        "layers": [],
        "entity_counts": {},
        "texts": [],
        "blocks": [],
        "dimensions": [],
        "layout_extents": {},
    }

    # Единицы измерения — важно для трактовки размеров.
    try:
        out["units"] = str(doc.header.get("$INSUNITS", ""))
    except Exception:
        pass

    layers = {}
    counts: dict[str, int] = {}

    for e in msp:
        t = e.dxftype()
        counts[t] = counts.get(t, 0) + 1
        try:
            layer = e.dxf.layer
        except Exception:
            layer = "(без слоя)"
        info = layers.setdefault(layer, {"entities": 0, "texts": 0, "blocks": 0})
        info["entities"] += 1

        if t in ("TEXT", "MTEXT", "ATTRIB", "ATTDEF"):
            s = _text_of(e).strip()
            if s:
                info["texts"] += 1
                if len(out["texts"]) < max_texts:
                    pos = ""
                    try:
                        ins = e.dxf.insert
                        pos = f"{float(ins.x):.1f};{float(ins.y):.1f}"
                    except Exception:
                        pass
                    out["texts"].append({"text": s[:300], "layer": layer, "pos": pos})
        elif t == "INSERT":
            info["blocks"] += 1
            name, attrs = "", []
            try:
                name = e.dxf.name or ""
            except Exception:
                pass
            try:
                for a in e.attribs:
                    av = _text_of(a).strip()
                    if av:
                        attrs.append(av[:200])
            except Exception:
                pass
            pos = ""
            try:
                ins = e.dxf.insert
                pos = f"{float(ins.x):.1f};{float(ins.y):.1f}"
            except Exception:
                pass
            out["blocks"].append({
                "name": name[:200], "layer": layer, "pos": pos,
                "attributes": attrs[:20],
            })
        elif t == "DIMENSION":
            try:
                txt = _text_of(e).strip()
                out["dimensions"].append({"text": txt[:200], "layer": layer})
            except Exception:
                pass

    out["entity_counts"] = dict(sorted(counts.items(), key=lambda kv: -kv[1]))
    out["layers"] = [{"name": k, **v} for k, v in
                      sorted(layers.items(), key=lambda kv: -kv[1]["entities"])]
    return out


def render_dxf_to_png(dxf_path: str, png_path: str, width: int = 2000) -> tuple[bool, str]:
    """Рисует DXF в PNG для передачи vision-модели.

    Возвращает (получилось_ли, описание_ошибки).
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import ezdxf
        from ezdxf.addons.drawing import Frontend, RenderContext
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    except Exception as e:
        return False, (
            f"рендеринг чертежа недоступен: не установлены ezdxf/matplotlib ({type(e).__name__}). "
            "Установите их: pip install ezdxf matplotlib"
        )

    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
    except Exception as e:
        return False, f"не удалось прочитать DXF: {type(e).__name__}: {e}"

    if not len(list(msp)):
        return False, "модельное пространство чертежа пусто — рисовать нечего."

    try:
        height = int(width * 0.7) or 1400
        fig = plt.figure(figsize=(width / 100, height / 100), dpi=100)
        ax = fig.add_axes([0, 0, 1, 1])
        ctx = RenderContext(doc)
        backend = MatplotlibBackend(ax)
        try:
            Frontend(ctx, backend).draw_layout(msp, finalize=True)
        except TypeError:
            # Совместимость со старыми версиями ezdxf
            Frontend(ctx, out=backend).draw_layout(msp)
        ax.set_aspect("equal")
        ax.axis("off")
        fig.savefig(png_path, dpi=100, facecolor="white", bbox_inches="tight")
        plt.close(fig)
        return True, ""
    except Exception as e:
        return False, f"ошибка рендеринга: {type(e).__name__}: {e}"


def is_dxf(path: str) -> bool:
    return path.lower().endswith(".dxf")


def is_dwg(path: str) -> bool:
    return path.lower().endswith(".dwg")


def describe_structure(structure: dict, max_chars: int = 4000) -> str:
    """Превращает структуру чертежа в компактное текстовое описание для модели."""
    if not structure:
        return ""
    lines = []
    lines.append(f"Версия DXF: {structure.get('dxf_version') or 'не указана'}")
    if structure.get("units"):
        lines.append(f"Единицы ($INSUNITS): {structure['units']}")

    counts = structure.get("entity_counts") or {}
    if counts:
        lines.append("Примитивы: " + ", ".join(
            f"{k}={v}" for k, v in list(counts.items())[:15]))

    layers = structure.get("layers") or []
    if layers:
        lines.append("Слои:")
        for l in layers[:25]:
            lines.append(
                f"  - {l.get('name')}: объектов={l.get('entities', 0)}, "
                f"надписей={l.get('texts', 0)}, блоков={l.get('blocks', 0)}"
            )

    texts = structure.get("texts") or []
    if texts:
        lines.append(f"Надписи на чертеже ({len(texts)}):")
        for t in texts[:120]:
            lines.append(f"  - [{t.get('layer')}] {t.get('text')}")

    blocks = structure.get("blocks") or []
    if blocks:
        lines.append(f"Вставки блоков ({len(blocks)}):")
        for b in blocks[:120]:
            extra = ("; атрибуты: " + ", ".join(b["attributes"][:6])) if b.get("attributes") else ""
            lines.append(f"  - {b.get('name')}{extra}")

    dims = structure.get("dimensions") or []
    if dims:
        lines.append(f"Размерные надписи ({len(dims)}):")
        for d in dims[:40]:
            if d.get("text"):
                lines.append(f"  - {d['text']}")

    text = "\n".join(lines)
    return text[:max_chars]