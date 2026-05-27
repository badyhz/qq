"""PRD Planning Final Status Report — T880."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class PrdPlanningFinalStatusReport:
    task_range: str
    completed_count: int
    planner_components: List[str]
    verification_summary: str
    final_status: str
    next_safe_phase: str
    hard_stop: str
    notes: List[str]


DEFAULT_PLANNER_COMPONENTS = [
    "prd_backlog_schema (T873)",
    "prd_milestone_planner (T874)",
    "prd_wave_planner (T875)",
    "prd_batch_planner (T876)",
    "prd_dependency_graph_validator (T877)",
    "prd_task_risk_classifier (T878)",
    "prd_agent_execution_window_recommender (T879)",
    "prd_backlog_seed_packet (T880)",
]


def build_prd_planning_final_status_report(
    task_range: str = "T873-T880",
    completed_count: int = 8,
    planner_components: List[str] | None = None,
    verification_summary: str = "all 8 planning components implemented and tested",
    final_status: str = "PASS",
    next_safe_phase: str = "T881-T900 — requires human approval",
    hard_stop: str = "T880",
    notes: List[str] | None = None,
) -> PrdPlanningFinalStatusReport:
    if planner_components is None:
        planner_components = list(DEFAULT_PLANNER_COMPONENTS)
    if notes is None:
        notes = [
            "PRD planning layer T873-T880 complete",
            "seed packet created for 500+ task backlog",
            "no live trading authorization — M8 frozen",
            "next phase T881-T900 requires human review",
        ]
    return PrdPlanningFinalStatusReport(
        task_range=task_range,
        completed_count=completed_count,
        planner_components=list(planner_components),
        verification_summary=verification_summary,
        final_status=final_status,
        next_safe_phase=next_safe_phase,
        hard_stop=hard_stop,
        notes=list(notes),
    )


def planning_final_status_report_to_dict(
    report: PrdPlanningFinalStatusReport,
) -> Dict:
    return {
        "task_range": report.task_range,
        "completed_count": report.completed_count,
        "planner_components": list(report.planner_components),
        "verification_summary": report.verification_summary,
        "final_status": report.final_status,
        "next_safe_phase": report.next_safe_phase,
        "hard_stop": report.hard_stop,
        "notes": list(report.notes),
    }


def planning_final_status_report_to_markdown(
    report: PrdPlanningFinalStatusReport,
) -> str:
    components_lines = "\n".join(
        f"- {c}" for c in report.planner_components
    )
    notes_lines = "\n".join(f"- {n}" for n in report.notes)
    return (
        f"# PRD Planning Final Status Report\n\n"
        f"**Task Range:** {report.task_range}\n"
        f"**Completed Count:** {report.completed_count}\n"
        f"**Verification Summary:** {report.verification_summary}\n"
        f"**Final Status:** {report.final_status}\n"
        f"**Next Safe Phase:** {report.next_safe_phase}\n"
        f"**Hard Stop:** {report.hard_stop}\n\n"
        f"## Planner Components\n\n{components_lines}\n\n"
        f"## Notes\n\n{notes_lines}\n"
    )
