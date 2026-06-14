"""MACD rebound scanner deployment audit."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class AuditCheck:
    check_id: str
    component: str
    status: str
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "component": self.component,
                "status": self.status, "detail": self.detail}


@dataclass(frozen=True)
class DeploymentAudit:
    audit_id: str
    created_at: str
    scanner_path: str
    checks: tuple[AuditCheck, ...]
    final_verdict: str
    def to_dict(self) -> dict:
        return {"audit_id": self.audit_id, "created_at": self.created_at,
                "scanner_path": self.scanner_path, "checks": [c.to_dict() for c in self.checks],
                "final_verdict": self.final_verdict}


DEPLOY_ARTIFACTS = (
    ("deploy/systemd/macd-rebound-scanner.service", "systemd service unit"),
    ("deploy/logrotate.d/macd-rebound-scanner", "logrotate config"),
    ("requirements.txt", "Python dependencies"),
    ("README.md", "Documentation"),
    ("config.yaml", "Scanner configuration"),
)


def run_audit(scanner_path: str) -> DeploymentAudit:
    root = pathlib.Path(scanner_path)
    checks: list[AuditCheck] = []
    for rel_path, description in DEPLOY_ARTIFACTS:
        exists = (root / rel_path).exists()
        checks.append(AuditCheck(
            f"DA_{rel_path.replace('/', '_').replace('.', '_')}",
            rel_path,
            "PRESENT" if exists else "MISSING",
            f"{description}: {'found' if exists else 'not found'}"))
    # Check if systemd service references correct paths
    svc_path = root / "deploy" / "systemd" / "macd-rebound-scanner.service"
    if svc_path.exists():
        content = svc_path.read_text(encoding="utf-8")
        if ".env" in content:
            checks.append(AuditCheck("DA_env_reference", "systemd", "INFO",
                "Service references .env file for credentials"))
        if "WorkingDirectory" in content:
            checks.append(AuditCheck("DA_working_dir", "systemd", "INFO",
                "Service has WorkingDirectory configured"))
    # Server path hint
    server_path = "/www/wwwroot/quant_monitor/macd_rebound_scanner"
    if root == pathlib.Path(server_path):
        checks.append(AuditCheck("DA_server_path", "deployment", "INFO",
            "Running from server path. Check: systemctl status macd-rebound-scanner"))
    else:
        checks.append(AuditCheck("DA_server_path", "deployment", "INFO",
            f"Not at server path ({server_path}). Server deploy commands available when at server path."))
    return DeploymentAudit(
        audit_id=f"MRD_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        scanner_path=str(root),
        checks=tuple(checks),
        final_verdict="MACD_REBOUND_DEPLOYMENT_AUDIT_READY|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )


def write_audit(audit: DeploymentAudit, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(audit.to_dict(), indent=2), encoding="utf-8")


def render_report(audit: DeploymentAudit) -> str:
    lines = ["# MACD Rebound Deployment Audit", "",
        f"**audit_id={audit.audit_id}**",
        f"**scanner_path={audit.scanner_path}**", "",
        "## Checks", "",
        "| Component | Status | Detail |",
        "|-----------|--------|--------|"]
    for c in audit.checks:
        lines.append(f"| {c.component} | {c.status} | {c.detail} |")
    lines.extend(["", "## Server Commands (when at server path)", "",
        "```bash", "systemctl status macd-rebound-scanner",
        "journalctl -u macd-rebound-scanner -n 100 --no-pager", "```", "",
        "## Conclusion", "", audit.final_verdict, ""])
    return "\n".join(lines)
