"""Плагины распознавания инженерных чертежей (DWG / DXF).

Два отдельных плагина, потому что они требуют разного:

  CadStructureChecker — разбор структуры чертежа. Модель ИИ не нужна вовсе.
    Достаточно ODA File Converter (для DWG) и библиотеки ezdxf. Извлекаются
    слои, надписи, вставки блоков, атрибуты, примитивы. Это детерминированная
    работа с данными, а не догадки.

  DwgVisionChecker — понимание того, что изображено на чертеже (однолинейная
    схема, план, спецификация, что обозначает конкретный символ).
    Требуется мультимодальная (vision) модель: чертеж рисуется в PNG и
    отправляется модели. Без такой модели проверка не проводится.

Ни один из плагинов не выдумывает содержимое чертежа. Если конвертация
не удалась или модель недоступна — возвращается not_performed с причиной.
"""
import os
import tempfile

from checkers.base import CheckResult
from services.ai_plugins.base import CAP_VISION, AIPlugin, PluginContext
from services.ai_plugins import cad


def _drawing_paths(ctx: PluginContext) -> list[str]:
    """Список файлов чертежей (DWG/DXF), которые есть физически на диске."""
    raw = ctx.data.get("drawing_paths") or ctx.dwg_paths
    out = []
    for p in raw or []:
        if p and os.path.exists(p):
            out.append(p)
    return out


def _prepare_dxf(path: str, workdir: str) -> tuple[str | None, str]:
    """Готовит DXF из DWG или DXF. Возвращает (путь_к_dxf, описание_ошибки)."""
    if cad.is_dxf(path):
        return path, ""
    if cad.is_dwg(path):
        dxf, err = cad.convert_dwg_to_dxf(path, outdir=workdir)
        return dxf, err
    return None, f"неподдерживаемый формат чертежа: {os.path.basename(path)}"


class CadStructureChecker(AIPlugin):
    """Структурный разбор чертежа. Модель ИИ не требуется."""

    code = "CAD_STRUCTURE"
    name = "Распознавание структуры чертежей (DWG, DXF)"
    category = "critical"
    needs_model = False
    ntd_refs = ("ГОСТ 21.208-2013; ГОСТ 21.210-2014; ГОСТ Р 21.101-2026 "
                "(условные обозначения на чертежах)")
    description = (
        "Извлекает из чертежей слои, надписи, вставки блоков и атрибуты. "
        "Не требует модели ИИ: работает с данными чертежа напрямую."
    )

    def availability(self, ctx: PluginContext) -> tuple[bool, str]:
        if not _drawing_paths(ctx):
            return False, (
                "Чертежи (DWG/DXF) не найдены среди загруженных файлов — "
                "структурный разбор не выполнялся."
            )
        has_dwg = any(cad.is_dwg(p) for p in _drawing_paths(ctx))
        if has_dwg:
            ok, detail = cad.oda_available()
            if not ok:
                return False, (
                    "Чертежи в формате DWG, а ODA File Converter не установлен. "
                    + detail
                )
        try:
            import ezdxf  # noqa: F401
        except Exception:
            return False, (
                "Для разбора чертежей нужна библиотека ezdxf — она не установлена. "
                "Установите её: pip install ezdxf"
            )
        return True, ""

    def run(self, ctx: PluginContext) -> CheckResult:
        paths = _drawing_paths(ctx)
        workdir = tempfile.mkdtemp(prefix="doccheck_cad_")
        structures: list[dict] = []
        failures: list[str] = []
        converted = 0

        for path in paths:
            name = os.path.basename(path)
            dxf, err = _prepare_dxf(path, workdir)
            if not dxf:
                failures.append(f"{name}: {err}")
                continue
            if cad.is_dwg(path):
                converted += 1
            st = cad.extract_dxf_structure(dxf)
            if not st:
                failures.append(
                    f"{name}: DXF получен, но разобрать его не удалось "
                    "(возможно, это не инженерный чертёж)"
                )
                continue
            st["file"] = name
            st["dxf_path"] = dxf
            structures.append(st)

        if not structures:
            return self._not_performed(
                reason="Не удалось извлечь структуру ни одного чертежа.",
                detail="; ".join(failures)[:800] or "причина не установлена",
            )

        total_texts = sum(len(s.get("texts") or []) for s in structures)
        total_blocks = sum(len(s.get("blocks") or []) for s in structures)
        total_layers = sum(len(s.get("layers") or []) for s in structures)

        summary = (
            f"Обработано чертежей: {len(structures)} из {len(paths)}"
            + (f" (конвертировано из DWG: {converted})" if converted else "")
            + f". Слоёв: {total_layers}, надписей: {total_texts}, "
            f"вставок блоков: {total_blocks}."
        )
        if failures:
            summary += f" Не обработано: {len(failures)} — " + "; ".join(failures[:5])

        return self._ok(
            detail=summary,
            evidence=[{"type": "drawings", "items": [
                {
                    "file": s["file"],
                    "version": s.get("dxf_version"),
                    "units": s.get("units"),
                    "layers": s.get("layers")[:20],
                    "texts": (s.get("texts") or [])[:60],
                    "blocks": (s.get("blocks") or [])[:60],
                } for s in structures
            ]}],
        )


class DwgVisionChecker(AIPlugin):
    """Понимание содержимого чертежа мультимодальной моделью."""

    code = "AI_CAD_VISION"
    name = "ИИ-распознавание чертежей по изображению (vision-модель)"
    category = "non-critical"
    capability = CAP_VISION
    needs_model = True
    ntd_refs = ("ГОСТ 21.208-2013; ГОСТ 21.210-2014; "
                "СП 484.1311500.2020; СП 486.1311500.2020")
    description = (
        "Чертёж конвертируется в PNG и анализируется мультимодальной моделью: "
        "определяется тип чертежа, состав оборудования и видимые отклонения."
    )

    def availability(self, ctx: PluginContext) -> tuple[bool, str]:
        ok, reason = super().availability(ctx)
        if not ok:
            return ok, reason
        if not _drawing_paths(ctx):
            return False, "Чертежи (DWG/DXF) не найдены — vision-анализ не выполнялся."
        has_dwg = any(cad.is_dwg(p) for p in _drawing_paths(ctx))
        if has_dwg:
            ok, detail = cad.oda_available()
            if not ok:
                return False, "Чертежи в формате DWG, а ODA File Converter не установлен. " + detail
        return True, ""

    def run(self, ctx: PluginContext) -> CheckResult:
        from services.ai_service import chat_multimodal
        from services.ai_plugins.llm_document import _extract_json

        paths = _drawing_paths(ctx)
        workdir = tempfile.mkdtemp(prefix="doccheck_cad_v_")
        findings: list[dict] = []
        processed = 0
        failures: list[str] = []

        for path in paths:
            name = os.path.basename(path)
            dxf, err = _prepare_dxf(path, workdir)
            if not dxf:
                failures.append(f"{name}: {err}")
                continue

            png = os.path.join(workdir, name.rsplit(".", 1)[0] + ".png")
            ok, rerr = cad.render_dxf_to_png(dxf, png)
            if not ok:
                failures.append(f"{name}: {rerr}")
                continue
            if not os.path.exists(png):
                failures.append(f"{name}: PNG не создан")
                continue

            # Структурная подпись помогает модели сориентироваться, но вывод
            # строится именно по картинке.
            st = cad.extract_dxf_structure(dxf) or {}
            hint = cad.describe_structure(st, max_chars=1500)

            resp = chat_multimodal(
                ctx.model, png, SYSTEM_PROMPT_CAD,
                f"Файл чертежа: {name}\n"
                f"Дополнительные сведения о структуре чертежа (из DXF, автоматически):\n{hint}\n",
            )
            if not resp.get("ok"):
                failures.append(f"{name}: {resp.get('error')}")
                continue

            data = _extract_json(resp.get("text", ""))
            if not isinstance(data, dict):
                failures.append(f"{name}: ответ модели не удалось разобрать как JSON")
                continue

            processed += 1
            for it in data.get("issues") or []:
                if isinstance(it, dict) and (it.get("comment") or "").strip():
                    findings.append({
                        "file": name,
                        "severity": (it.get("severity") or "non-critical").lower(),
                        "comment": (it.get("comment") or "").strip()[:800],
                        "ntd": (it.get("ntd") or "").strip()[:200],
                    })
            if (data.get("drawing_type") or "").strip():
                findings.append({
                    "file": name,
                    "severity": "info",
                    "comment": f"Тип чертежа по классификации модели: "
                               f"{str(data['drawing_type']).strip()[:200]}",
                    "ntd": "",
                })

        if processed == 0:
            return self._not_performed(
                reason="Ни один чертёж не удалось проанализировать моделью.",
                detail="; ".join(failures)[:800] or "причина не установлена",
            )

        summary = f"Проанализировано чертежей: {processed} из {len(paths)}."
        if failures:
            summary += f" Не обработано: {len(failures)} — " + "; ".join(failures[:5])

        real = [f for f in findings if f["severity"] != "info"]
        if not real:
            return self._ok(detail=summary + " Замечаний по НТД не выявлено.",
                            evidence=[{"type": "cad_findings", "items": findings[:60]}])
        crit = [f for f in real if f["severity"] == "critical"]
        return self._fail(
            detail=summary + f" Замечаний: {len(real)}, критических: {len(crit)}.",
            evidence=[{"type": "cad_findings", "items": findings[:60]}],
        )


SYSTEM_PROMPT_CAD = (
    "Ты — инженер, который смотрит на чертёж инженерных систем здания "
    "(электроснабжение, электроосвещение, пожарная сигнализация, СОУЭ, "
    "пожаротушение, СКС, видеонаблюдение, СКУД) и проверяет его на "
    "соответствие нормативно-техническим требованиям РФ.\n\n"
    "ЖЁСТКИЕ ПРАВИЛА:\n"
    "1. Опирайся ТОЛЬКО на то, что реально изображено на чертеже.\n"
    "2. Не выдумывай оборудование, марки, сечения, расстояния и номера пунктов НТД.\n"
    "3. Если чертёж нечитаем, обрезан или это не чертёж инженерных систем — "
    "верни drawing_type: 'не определён' и пустой список issues.\n"
    "4. Указывай пункт НТД только если ты действительно знаю, что он применим.\n\n"
    "ОТВЕТ — СТРОГО JSON без пояснений:\n"
    '{"drawing_type": "тип чертежа или «не определён»", '
    '"issues": [{"severity": "critical|non-critical", '
    '"comment": "что не так на чертеже", "ntd": "пункт НТД или пустая строка"}]}'
)