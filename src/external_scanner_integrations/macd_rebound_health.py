"""MACD rebound scanner health check."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class HealthCheck:
    check_id: str
    component: str
    status: str
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "component": self.component,
                "status": self.status, "detail": self.detail}


@dataclass(frozen=True)
class HealthReport:
    report_id: str
    created_at: str
    scanner_path: str
    checks: tuple[HealthCheck, ...]
    health_score: int
    final_verdict: str
    def to_dict(self) -> dict:
        return {"report_id": self.report_id, "created_at": self.created_at,
                "scanner_path": self.scanner_path, "checks": [c.to_dict() for c in self.checks],
                "health_score": self.health_score, "final_verdict": self.final_verdict}


def run_health_check(scanner_path: str) -> HealthReport:
    root = pathlib.Path(scanner_path)
    checks: list[HealthCheck] = []
    # Core files
    for fname in ("main.py", "config.yaml", "requirements.txt"):
        exists = (root / fname).exists()
        checks.append(HealthCheck(f"HC_{fname}", fname, "OK" if exists else "MISSING",
            f"{fname} {'found' if exists else 'not found'}"))
    # Directories
    for dname in ("src", "tests", "logs", "data", "deploy"):
        exists = (root / dname).is_dir()
        checks.append(HealthCheck(f"HC_{dname}", dname, "OK" if exists else "MISSING",
            f"{dname}/ {'exists' if exists else 'not found'}"))
    # Runtime files
    for rname in ("logs/alerts.jsonl", "logs/scan_detail.jsonl", "data/signals.csv"):
        exists = (root / rname).exists()
        checks.append(HealthCheck(f"HC_{rname}", rname, "OK" if exists else "MISSING",
            f"{rname} {'exists' if exists else 'not found'}"))
    # Errors log
    errors_path = root / "logs" / "errors.log"
    if errors_path.exists():
        content = errors_path.read_text(encoding="utf-8").strip()
        checks.append(HealthCheck("HC_errors_log", "errors.log",
            "OK" if not content else "HAS_ERRORS",
            f"errors.log {'empty (good)' if not content else f'has content ({len(content)} bytes)'}"))
    else:
        checks.append(HealthCheck("HC_errors_log", "errors.log", "MISSING", "errors.log not found"))
    # Deploy files
    for deploy_file in ("deploy/systemd/macd-rebound-scanner.service", "deploy/logrotate.d/macd-rebound-scanner"):
        exists = (root / deploy_file).exists()
        checks.append(HealthCheck(f"HC_{deploy_file}", deploy_file, "OK" if exists else "MISSING",
            f"{deploy_file} {'found' if exists else 'not found'}"))
    # Score
    ok_count = sum(1 for c in checks if c.status == "OK")
    score = round(ok_count / len(checks) * 100) if checks else 0
    return HealthReport(
        report_id=f"MRH_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        scanner_path=str(root),
        checks=tuple(checks),
        health_score=score,
        final_verdict=f"MACD_REBOUND_EXTERNAL_SCANNER_HEALTH_READY|SCORE={score}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )


def write_report(report: HealthReport, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")


def render_report(report: HealthReport) -> str:
    lines = ["# MACD Rebound Scanner Health Report", "",
        f"**report_id={report.report_id}**",
        f"**scanner_path={report.scanner_path}**",
        f"**health_score={report.health_score}%**", "",
        "## Checks", "",
        "| Component | Status | Detail |",
        "|-----------|--------|--------|"]
    for c in report.checks:
        lines.append(f"| {c.component} | {c.status} | {c.detail} |")
    lines.extend(["", "## Conclusion", "", report.final_verdict, ""])
    return "\n".join(lines)
