"""T850: Runtime governance read-only final status report.

Pure, deterministic, no I/O, no timestamps, no random.
Covers T826-T850 read-only governance design phase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyFinalStatusReport:
    """Final status report for read-only governance design phase."""

    task_range: str
    completed_count: int
    test_summary: str
    final_status: str
    next_safe_phase: str
    frozen_items: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


def build_readonly_final_status_report() -> RuntimeGovernanceReadOnlyFinalStatusReport:
    """Build the final status report with canonical defaults."""
    return RuntimeGovernanceReadOnlyFinalStatusReport(
        task_range="T826-T850",
        completed_count=25,
        test_summary="all readonly tests passing",
        final_status="PASS",
        next_safe_phase="manual review of read-only hook design",
        frozen_items=[
            "no live trading",
            "no real execution",
            "no secret access",
            "no network call",
            "no planner integration",
        ],
        notes=[
            "All read-only design tasks complete.",
            "No live authorization in this phase.",
            "Manual review required before any implementation.",
        ],
    )


def readonly_final_status_report_to_dict(
    report: RuntimeGovernanceReadOnlyFinalStatusReport,
) -> Dict[str, object]:
    """Convert report to dict."""
    return {
        "task_range": report.task_range,
        "completed_count": report.completed_count,
        "test_summary": report.test_summary,
        "final_status": report.final_status,
        "next_safe_phase": report.next_safe_phase,
        "frozen_items": list(report.frozen_items),
        "notes": list(report.notes),
    }


def readonly_final_status_report_to_markdown(
    report: RuntimeGovernanceReadOnlyFinalStatusReport,
) -> str:
    """Convert report to markdown string."""
    frozen_lines = "\n".join(f"- {item}" for item in report.frozen_items)
    note_lines = "\n".join(f"- {n}" for n in report.notes)
    return (
        f"# Runtime Governance Read-Only Final Status Report\n\n"
        f"**Task Range:** {report.task_range}\n"
        f"**Completed:** {report.completed_count}\n"
        f"**Test Summary:** {report.test_summary}\n"
        f"**Final Status:** {report.final_status}\n"
        f"**Next Safe Phase:** {report.next_safe_phase}\n\n"
        f"## Frozen Items\n\n{frozen_lines}\n\n"
        f"## Notes\n\n{note_lines}\n"
    )
