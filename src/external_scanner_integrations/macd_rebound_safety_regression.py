"""MACD rebound scanner integration safety regression."""
from __future__ import annotations
import json, pathlib, re, uuid
from dataclasses import dataclass
from datetime import datetime, timezone

FORBIDDEN_IMPORTS = ("ccxt", "requests", "httpx", "aiohttp", "websocket")
FORBIDDEN_PATTERNS = (
    "submit_order", "cancel_order", "create_order",
    "privatePost", "privateGet", "fapiPrivate",
)
REAL_ENDPOINTS = (
    "api.binance.com", "fapi.binance.com", "testnet.binance.vision",
)
INTEGRATION_ROOT = pathlib.Path(__file__).resolve().parent


@dataclass(frozen=True)
class RegressionCheck:
    check_id: str
    file: str
    status: str
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "file": self.file,
                "status": self.status, "detail": self.detail}


@dataclass(frozen=True)
class SafetyRegressionReport:
    report_id: str
    created_at: str
    checks: tuple[RegressionCheck, ...]
    total_checked: int
    total_clean: int
    total_flagged: int
    final_verdict: str
    def to_dict(self) -> dict:
        return {"report_id": self.report_id, "created_at": self.created_at,
                "checks": [c.to_dict() for c in self.checks],
                "total_checked": self.total_checked,
                "total_clean": self.total_clean,
                "total_flagged": self.total_flagged,
                "final_verdict": self.final_verdict}


def _scan_file(path: pathlib.Path) -> list[RegressionCheck]:
    checks: list[RegressionCheck] = []
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return checks
    rel = str(path.relative_to(INTEGRATION_ROOT))
    # Forbidden imports
    for imp in FORBIDDEN_IMPORTS:
        pattern = rf'^\s*(import|from)\s+{re.escape(imp)}\b'
        if re.search(pattern, content, re.MULTILINE):
            checks.append(RegressionCheck(
                f"SR_{rel}_{imp}", rel, "FLAGGED",
                f"Forbidden import: {imp}"))
    # Forbidden patterns
    for pat in FORBIDDEN_PATTERNS:
        if pat in content:
            checks.append(RegressionCheck(
                f"SR_{rel}_{pat}", rel, "FLAGGED",
                f"Forbidden pattern: {pat}"))
    # Real endpoints
    for ep in REAL_ENDPOINTS:
        if ep in content:
            checks.append(RegressionCheck(
                f"SR_{rel}_{ep.replace('.', '_')}", rel, "FLAGGED",
                f"Real endpoint reference: {ep}"))
    if not checks:
        checks.append(RegressionCheck(
            f"SR_{rel}_clean", rel, "CLEAN", "No forbidden patterns found"))
    return checks


def run_safety_regression() -> SafetyRegressionReport:
    checks: list[RegressionCheck] = []
    py_files = sorted(INTEGRATION_ROOT.glob("*.py"))
    for f in py_files:
        if f.name == "macd_rebound_safety_regression.py":
            continue
        checks.extend(_scan_file(f))
    total = len([c for c in checks if c.status in ("CLEAN", "FLAGGED")])
    clean = sum(1 for c in checks if c.status == "CLEAN")
    flagged = sum(1 for c in checks if c.status == "FLAGGED")
    verdict = "MACD_REBOUND_SAFETY_REGRESSION_PASS" if flagged == 0 else "MACD_REBOUND_SAFETY_REGRESSION_FLAGGED"
    return SafetyRegressionReport(
        report_id=f"MSR_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        checks=tuple(checks),
        total_checked=total,
        total_clean=clean,
        total_flagged=flagged,
        final_verdict=f"{verdict}|FILES={total}|FLAGGED={flagged}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )


def write_report(report: SafetyRegressionReport, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")


def render_report(report: SafetyRegressionReport) -> str:
    lines = ["# MACD Rebound Safety Regression", "",
        f"**report_id={report.report_id}**",
        f"**total_checked={report.total_checked}**",
        f"**total_clean={report.total_clean}**",
        f"**total_flagged={report.total_flagged}**", "",
        "## Checks", "",
        "| File | Status | Detail |",
        "|------|--------|--------|"]
    for c in report.checks:
        lines.append(f"| {c.file} | {c.status} | {c.detail} |")
    lines.extend(["", "## Conclusion", "", report.final_verdict, ""])
    return "\n".join(lines)
