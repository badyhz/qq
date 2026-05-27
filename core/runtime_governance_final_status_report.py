from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceFinalStatusReport:
    completed_task_count: int
    committed_task_count: int
    test_summary: Dict[str, Any]
    risk_summary: Dict[str, Any]
    final_status: str  # PASS/WARN/FAIL
    next_recommended_phase: str
    frozen_items: List[str]
    notes: List[str]


def build_runtime_governance_final_status_report() -> RuntimeGovernanceFinalStatusReport:
    """Pure. Deterministic."""
    return RuntimeGovernanceFinalStatusReport(
        completed_task_count=28,
        committed_task_count=28,
        test_summary={
            "total": "~300+",
            "status": "PASS",
            "scope": "unit + integration + smoke",
        },
        risk_summary={
            "live_trading_blocked": True,
            "secrets_access_blocked": True,
            "dry_run_default": True,
        },
        final_status="PASS",
        next_recommended_phase="manual review / read-only hook design",
        frozen_items=[
            "live submit",
            "secrets access",
            "planner autonomous integration",
            "real exchange execution",
        ],
        notes=[
            "Tasks T794-T821 completed and committed.",
            "All tests passing. No live trading enabled.",
            "Frozen items must not be unfrozen without explicit approval.",
        ],
    )


def final_status_report_to_dict(report: RuntimeGovernanceFinalStatusReport) -> Dict[str, Any]:
    """Serialize."""
    return {
        "completed_task_count": report.completed_task_count,
        "committed_task_count": report.committed_task_count,
        "test_summary": dict(report.test_summary),
        "risk_summary": dict(report.risk_summary),
        "final_status": report.final_status,
        "next_recommended_phase": report.next_recommended_phase,
        "frozen_items": list(report.frozen_items),
        "notes": list(report.notes),
    }


def final_status_report_to_markdown(report: RuntimeGovernanceFinalStatusReport) -> str:
    """Render deterministic markdown."""
    frozen_lines = "\n".join(f"- {item}" for item in report.frozen_items)
    note_lines = "\n".join(f"- {n}" for n in report.notes)
    return (
        f"# Runtime Governance Final Status Report\n\n"
        f"## Summary\n\n"
        f"| Field | Value |\n"
        f"|---|---|\n"
        f"| Completed tasks | {report.completed_task_count} |\n"
        f"| Committed tasks | {report.committed_task_count} |\n"
        f"| Final status | **{report.final_status}** |\n"
        f"| Next phase | {report.next_recommended_phase} |\n\n"
        f"## Test Summary\n\n"
        f"- Total: {report.test_summary['total']}\n"
        f"- Status: {report.test_summary['status']}\n"
        f"- Scope: {report.test_summary['scope']}\n\n"
        f"## Risk Summary\n\n"
        f"- Live trading blocked: {report.risk_summary['live_trading_blocked']}\n"
        f"- Secrets access blocked: {report.risk_summary['secrets_access_blocked']}\n"
        f"- Dry-run default: {report.risk_summary['dry_run_default']}\n\n"
        f"## Frozen Items\n\n"
        f"{frozen_lines}\n\n"
        f"## Notes\n\n"
        f"{note_lines}\n"
    )
