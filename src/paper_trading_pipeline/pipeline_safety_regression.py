"""Pipeline safety regression scanner."""
from __future__ import annotations
import json, pathlib, re
from dataclasses import dataclass
from datetime import datetime, timezone
from src.paper_trading_pipeline.models import new_id

FORBIDDEN_IMPORTS = ("ccxt", "requests", "httpx", "aiohttp", "websocket")
FORBIDDEN_PATTERNS = (
    "create_order", "submit_order", "cancel_order", "execute_trade",
    "live_order", "fapiPrivate", "privatePost", "privateGet",
    "api_key", "api_secret", "webhook_url", "FEISHU_WEBHOOK_URL",
    "FEISHU_SECRET", "load_dotenv",
)
REAL_ENDPOINTS = ("api.binance.com", "fapi.binance.com", "testnet.binance.vision")
PIPELINE_ROOT = pathlib.Path(__file__).resolve().parent


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
    rel = str(path.relative_to(PIPELINE_ROOT))
    for imp in FORBIDDEN_IMPORTS:
        pattern = rf'^\s*(import|from)\s+{re.escape(imp)}\b'
        if re.search(pattern, content, re.MULTILINE):
            checks.append(RegressionCheck(f"SR_{rel}_{imp}", rel, "FLAGGED",
                f"Forbidden import: {imp}"))
    for pat in FORBIDDEN_PATTERNS:
        if pat in content:
            checks.append(RegressionCheck(f"SR_{rel}_{pat}", rel, "FLAGGED",
                f"Forbidden pattern: {pat}"))
    for ep in REAL_ENDPOINTS:
        if ep in content:
            checks.append(RegressionCheck(f"SR_{rel}_{ep.replace('.', '_')}", rel, "FLAGGED",
                f"Real endpoint: {ep}"))
    if not checks:
        checks.append(RegressionCheck(f"SR_{rel}_clean", rel, "CLEAN", "No forbidden patterns"))
    return checks


def run_safety_regression() -> SafetyRegressionReport:
    checks: list[RegressionCheck] = []
    py_files = sorted(PIPELINE_ROOT.glob("*.py"))
    for f in py_files:
        if f.name == "pipeline_safety_regression.py":
            continue
        checks.extend(_scan_file(f))
    total = len([c for c in checks if c.status in ("CLEAN", "FLAGGED")])
    clean = sum(1 for c in checks if c.status == "CLEAN")
    flagged = sum(1 for c in checks if c.status == "FLAGGED")
    verdict = "PAPER_TRADING_PIPELINE_NO_SUBMIT_SAFETY_PASS" if flagged == 0 else "PAPER_TRADING_PIPELINE_SAFETY_FLAGGED"
    return SafetyRegressionReport(
        report_id=new_id("PSR"),
        created_at=datetime.now(timezone.utc).isoformat(),
        checks=tuple(checks),
        total_checked=total,
        total_clean=clean,
        total_flagged=flagged,
        final_verdict=f"{verdict}|FILES={total}|FLAGGED={flagged}|REAL_ORDER_SUBMIT_NOT_ALLOWED|REAL_TRADING_NOT_ALLOWED",
    )
