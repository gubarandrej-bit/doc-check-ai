"""Базовый интерфейс проверок.

Каждая проверка возвращает CheckResult со статусом:
  passed / failed / not_performed
При отсутствии исходных данных статус = not_performed и указывается причина.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckResult:
    code: str
    name: str
    category: str = "critical"  # critical | non-critical
    status: str = "not_performed"  # passed | failed | not_performed
    detail: str = ""
    ntd_refs: str = ""
    reason_skipped: str = ""
    evidence: list = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code, "name": self.name, "category": self.category,
            "status": self.status, "detail": self.detail, "ntd_refs": self.ntd_refs,
            "reason_skipped": self.reason_skipped, "evidence": self.evidence,
        }


class Checker:
    code: str = "BASE"
    name: str = "Базовая проверка"
    category: str = "critical"
    ntd_refs: str = ""

    def run(self, data: dict[str, Any]) -> CheckResult:
        raise NotImplementedError

    def _not_performed(self, reason: str, detail: str = "") -> CheckResult:
        return CheckResult(
            code=self.code, name=self.name, category=self.category,
            status="not_performed", detail=detail, ntd_refs=self.ntd_refs,
            reason_skipped=reason,
        )

    def _ok(self, detail: str = "", evidence: list | None = None) -> CheckResult:
        return CheckResult(
            code=self.code, name=self.name, category=self.category,
            status="passed", detail=detail, ntd_refs=self.ntd_refs, evidence=evidence or [],
        )

    def _fail(self, detail: str = "", evidence: list | None = None) -> CheckResult:
        return CheckResult(
            code=self.code, name=self.name, category=self.category,
            status="failed", detail=detail, ntd_refs=self.ntd_refs, evidence=evidence or [],
        )