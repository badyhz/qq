"""PRD Control Plane Final Status Report — T872."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class PrdControlPlaneFinalStatusReport:
    task_range: str
    completed_count: int
    test_summary: str
    final_status: str
    next_safe_phase: str
    hard_stop: str
    notes: List[str]


def build_prd_control_plane_final_status_report(
    task_range: str = "T865-T872",
    completed_count: int = 8,
    test_summary: str = "all tests pass",
    final_status: str = "PASS",
    next_safe_phase: str = "T873-T880 (requires human approval)",
    hard_stop: str = "T872",
    notes: List[str] | None = None,
) -> PrdControlPlaneFinalStatusReport:
    if notes is None:
        notes = [
            "PRD control plane foundation complete",
            "next phase requires human review before execution",
        ]
    return PrdControlPlaneFinalStatusReport(
        task_range=task_range,
        completed_count=completed_count,
        test_summary=test_summary,
        final_status=final_status,
        next_safe_phase=next_safe_phase,
        hard_stop=hard_stop,
        notes=list(notes),
    )


def prd_control_plane_final_status_report_to_dict(
    report: PrdControlPlaneFinalStatusReport,
) -> Dict:
    return {
        "task_range": report.task_range,
        "completed_count": report.completed_count,
        "test_summary": report.test_summary,
        "final_status": report.final_status,
        "next_safe_phase": report.next_safe_phase,
        "hard_stop": report.hard_stop,
        "notes": list(report.notes),
    }


def prd_control_plane_final_status_report_to_markdown(
    report: PrdControlPlaneFinalStatusReport,
) -> str:
    notes_lines = "\n".join(f"- {n}" for n in report.notes)
    return (
        f"# PRD Control Plane Final Status Report\n\n"
        f"**Task Range:** {report.task_range}\n"
        f"**Completed Count:** {report.completed_count}\n"
        f"**Test Summary:** {report.test_summary}\n"
        f"**Final Status:** {report.final_status}\n"
        f"**Next Safe Phase:** {report.next_safe_phase}\n"
        f"**Hard Stop:** {report.hard_stop}\n\n"
        f"## Notes\n\n{notes_lines}\n"
    )
