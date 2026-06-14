"""Deployment safety regression scanner."""
from __future__ import annotations
import pathlib, re
from dataclasses import dataclass
from datetime import datetime, timezone
from src.paper_trading_deployment.models import new_id

FORBIDDEN_IMPORTS = ("ccxt", "requests", "httpx", "aiohttp", "websocket")
FORBIDDEN_PATTERNS = (
    "create_order", "submit_order", "cancel_order", "execute_trade",
    "live_order", "fapiPrivate", "privatePost", "privateGet",
    "api_key", "api_secret", "webhook_url", "FEISHU_WEBHOOK_URL",
    "FEISHU_SECRET", "load_dotenv", "os.environ",
    "systemctl enable", "systemctl start", "systemctl restart",
    "crontab -e", "crontab -l", "rm -rf", "git reset --hard",
    ".env",
)
REAL_ENDPOINTS = ("api.binance.com", "fapi.binance.com", "testnet.binance.vision")

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SCAN_DIRS = (
    ROOT / "src" / "paper_trading_deployment",
)
SCAN_SCRIPTS = (
    "scripts/run_paper_ops_server_config_check.py",
    "scripts/run_paper_ops_deployment_preflight.py",
    "scripts/run_paper_ops_canary_dry_run.py",
    "scripts/run_paper_ops_install_plan.py",
    "scripts/run_paper_ops_runtime_layout_check.py",
    "scripts/run_paper_ops_server_health_report.py",
    "scripts/run_paper_ops_rollback_plan.py",
    "scripts/run_paper_ops_deployment_safety_regression.py",
    "scripts/run_paper_ops_deployment_suite.py",
)
SCAN_DEPLOY = (
    ROOT / "deploy" / "systemd",
    ROOT / "deploy" / "cron",
    ROOT / "deploy" / "logrotate.d",
)


@dataclass(frozen=True)
class SafetyCheck:
    check_id: str
    file: str
    status: str
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "file": self.file,
                "status": self.status, "detail": self.detail}


@dataclass(frozen=True)
class DeploymentSafetyReport:
    report_id: str
    created_at: str
    checks: tuple[SafetyCheck, ...]
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


def _scan_file(path: pathlib.Path, rel: str) -> list[SafetyCheck]:
    checks: list[SafetyCheck] = []
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return checks

    for imp in FORBIDDEN_IMPORTS:
        pattern = rf'^\s*(import|from)\s+{re.escape(imp)}\b'
        if re.search(pattern, content, re.MULTILINE):
            checks.append(SafetyCheck(f"DS_{rel}_{imp}", rel, "FLAGGED",
                f"Forbidden import: {imp}"))
    for pat in FORBIDDEN_PATTERNS:
        if pat in content:
            checks.append(SafetyCheck(f"DS_{rel}_{pat.replace(' ', '_')}", rel, "FLAGGED",
                f"Forbidden pattern: {pat}"))
    for ep in REAL_ENDPOINTS:
        if ep in content:
            checks.append(SafetyCheck(f"DS_{rel}_{ep.replace('.', '_')}", rel, "FLAGGED",
                f"Real endpoint: {ep}"))
    if not checks:
        checks.append(SafetyCheck(f"DS_{rel}_clean", rel, "CLEAN", "No forbidden patterns"))
    return checks


def run_safety_regression() -> DeploymentSafetyReport:
    checks: list[SafetyCheck] = []

    # Scan source dir (skip self)
    for d in SCAN_DIRS:
        if d.exists():
            for f in sorted(d.glob("*.py")):
                if f.name == "deployment_safety_regression.py":
                    continue
                rel = str(f.relative_to(ROOT))
                checks.extend(_scan_file(f, rel))

    # Scan scripts
    for s in SCAN_SCRIPTS:
        f = ROOT / s
        if f.exists():
            checks.extend(_scan_file(f, s))

    # Scan deploy examples
    for d in SCAN_DEPLOY:
        if d.exists():
            for f in sorted(d.glob("*")):
                rel = str(f.relative_to(ROOT))
                checks.extend(_scan_file(f, rel))

    # Scan config
    cfg_path = ROOT / "config" / "deployments" / "paper_trading_ops_server.example.yaml"
    if cfg_path.exists():
        checks.extend(_scan_file(cfg_path, str(cfg_path.relative_to(ROOT))))

    total = len(checks)
    clean = sum(1 for c in checks if c.status == "CLEAN")
    flagged = sum(1 for c in checks if c.status == "FLAGGED")
    verdict = "PAPER_OPS_DEPLOYMENT_NO_SUBMIT_SAFETY_PASS" if flagged == 0 else "PAPER_OPS_DEPLOYMENT_SAFETY_FLAGGED"

    return DeploymentSafetyReport(
        report_id=new_id("DSR"), created_at=datetime.now(timezone.utc).isoformat(),
        checks=tuple(checks), total_checked=total, total_clean=clean, total_flagged=flagged,
        final_verdict=f"{verdict}|FILES={total}|FLAGGED={flagged}|REAL_ORDER_SUBMIT_NOT_ALLOWED|REAL_TRADING_NOT_ALLOWED|NO_SYSTEMD_AUTO_INSTALL|NO_CRONTAB_AUTO_WRITE",
    )
