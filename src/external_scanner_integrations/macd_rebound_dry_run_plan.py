"""MACD rebound scanner dry-run plan."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class DryRunStep:
    step_id: str
    order: int
    action: str
    detail: str
    risk: str
    def to_dict(self) -> dict:
        return {"step_id": self.step_id, "order": self.order,
                "action": self.action, "detail": self.detail, "risk": self.risk}


@dataclass(frozen=True)
class DryRunPlan:
    plan_id: str
    created_at: str
    scanner_path: str
    steps: tuple[DryRunStep, ...]
    final_verdict: str
    def to_dict(self) -> dict:
        return {"plan_id": self.plan_id, "created_at": self.created_at,
                "scanner_path": self.scanner_path,
                "steps": [s.to_dict() for s in self.steps],
                "final_verdict": self.final_verdict}


def create_dry_run_plan(scanner_path: str) -> DryRunPlan:
    steps = (
        DryRunStep("DR_01", 1, "verify_config",
            "Load config.yaml, confirm dry_run=true and alert.dry_run=true",
            "LOW - read-only config inspection"),
        DryRunStep("DR_02", 2, "verify_scanner_health",
            "Run health check on scanner directory structure",
            "LOW - filesystem read only"),
        DryRunStep("DR_03", 3, "ingest_existing_logs",
            "Read signals.csv, alerts.jsonl, scan_detail.jsonl, errors.log",
            "LOW - read-only log parsing"),
        DryRunStep("DR_04", 4, "run_scanner_once_dry",
            "Execute: python main.py --once --dry-run",
            "MEDIUM - scanner runs but dry_run flag prevents real alerts"),
        DryRunStep("DR_05", 5, "verify_no_real_alerts",
            "Check alerts.jsonl for new entries with sent=true and dry_run=false",
            "LOW - log inspection after dry run"),
        DryRunStep("DR_06", 6, "verify_no_network_calls",
            "Check errors.log for webhook or network errors",
            "LOW - log inspection"),
        DryRunStep("DR_07", 7, "generate_daily_report",
            "Run daily report combining health and log data",
            "LOW - read-only aggregation"),
        DryRunStep("DR_08", 8, "deployment_audit",
            "Check deploy artifacts and systemd service config",
            "LOW - filesystem read only"),
        DryRunStep("DR_09", 9, "safety_regression",
            "Scan integration code for forbidden imports and patterns",
            "LOW - source code inspection"),
    )
    return DryRunPlan(
        plan_id=f"MDR_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        scanner_path=scanner_path,
        steps=steps,
        final_verdict="MACD_REBOUND_DRY_RUN_PLAN_READY|ALL_STEPS_READONLY_OR_DRY_RUN|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )


def write_plan(plan: DryRunPlan, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan.to_dict(), indent=2), encoding="utf-8")


def render_report(plan: DryRunPlan) -> str:
    lines = ["# MACD Rebound Dry-Run Plan", "",
        f"**plan_id={plan.plan_id}**",
        f"**scanner_path={plan.scanner_path}**", "",
        "## Steps", "",
        "| # | Action | Detail | Risk |",
        "|---|--------|--------|------|"]
    for s in plan.steps:
        lines.append(f"| {s.order} | {s.action} | {s.detail} | {s.risk} |")
    lines.extend(["", "## Conclusion", "", plan.final_verdict, ""])
    return "\n".join(lines)
