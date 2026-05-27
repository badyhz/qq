"""PRD task queue validator — T867.

Pure, deterministic, no I/O, no timestamps, no random.
Validates PRD task queue ranges and safety.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from core.prd_task_model import (
    PrdTask,
    VALID_RISK_LEVELS,
    VALID_STATUSES,
    parse_task_number,
    validate_task_id,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PrdTaskValidationIssue:
    issue_id: str
    task_id: str
    severity: str  # "blocker" | "warning"
    message: str
    category: str


@dataclass(frozen=True)
class PrdTaskQueueValidationReport:
    total_tasks: int
    issue_count: int
    blocker_count: int
    warning_count: int
    final_verdict: str  # PASS | WARN | BLOCKED | FAIL
    issues: tuple  # tuple[PrdTaskValidationIssue, ...]
    notes: tuple   # tuple[str, ...]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_FORBIDDEN_AUTO_EXEC_STATUSES = frozenset({
    "HUMAN_REVIEW_REQUIRED",
    "FROZEN",
})


def _validate_task_ids(tasks: List[PrdTask]) -> List[PrdTaskValidationIssue]:
    """Check all task IDs are valid T<digits> format."""
    issues: List[PrdTaskValidationIssue] = []
    for task in tasks:
        if not validate_task_id(task.task_id):
            issues.append(PrdTaskValidationIssue(
                issue_id=f"INVALID_ID_{len(issues)+1:03d}",
                task_id=task.task_id,
                severity="blocker",
                message=f"Invalid task ID format: {task.task_id!r}",
                category="invalid_id",
            ))
    return issues


def _validate_no_duplicates(tasks: List[PrdTask]) -> List[PrdTaskValidationIssue]:
    """Check for duplicate task IDs."""
    issues: List[PrdTaskValidationIssue] = []
    seen: set[str] = set()
    for task in tasks:
        if task.task_id in seen:
            issues.append(PrdTaskValidationIssue(
                issue_id=f"DUP_{len(issues)+1:03d}",
                task_id=task.task_id,
                severity="blocker",
                message=f"Duplicate task ID: {task.task_id}",
                category="duplicate",
            ))
        seen.add(task.task_id)
    return issues


def _validate_range_present(
    tasks: List[PrdTask],
    start_task_id: str,
    end_task_id: str,
) -> List[PrdTaskValidationIssue]:
    """Check that start and end task IDs exist in the task list."""
    issues: List[PrdTaskValidationIssue] = []
    ids = {t.task_id for t in tasks}
    if start_task_id not in ids:
        issues.append(PrdTaskValidationIssue(
            issue_id=f"MISSING_START_{len(issues)+1:03d}",
            task_id=start_task_id,
            severity="blocker",
            message=f"Start task {start_task_id} not found in task list",
            category="missing_range",
        ))
    if end_task_id not in ids:
        issues.append(PrdTaskValidationIssue(
            issue_id=f"MISSING_END_{len(issues)+1:03d}",
            task_id=end_task_id,
            severity="blocker",
            message=f"End task {end_task_id} not found in task list",
            category="missing_range",
        ))
    return issues


def _validate_range_order(
    start_task_id: str,
    end_task_id: str,
) -> List[PrdTaskValidationIssue]:
    """Check start <= end numerically."""
    issues: List[PrdTaskValidationIssue] = []
    try:
        start_num = parse_task_number(start_task_id)
        end_num = parse_task_number(end_task_id)
    except ValueError:
        return issues  # invalid ID already caught elsewhere
    if start_num > end_num:
        issues.append(PrdTaskValidationIssue(
            issue_id="RANGE_ORDER_001",
            task_id=start_task_id,
            severity="blocker",
            message=f"Start task {start_task_id} > end task {end_task_id}",
            category="range_order",
        ))
    return issues


def _validate_statuses(tasks: List[PrdTask]) -> List[PrdTaskValidationIssue]:
    """Check all tasks have valid statuses."""
    issues: List[PrdTaskValidationIssue] = []
    for task in tasks:
        if task.status not in VALID_STATUSES:
            issues.append(PrdTaskValidationIssue(
                issue_id=f"INVALID_STATUS_{len(issues)+1:03d}",
                task_id=task.task_id,
                severity="blocker",
                message=f"Invalid status {task.status!r} on {task.task_id}",
                category="invalid_status",
            ))
    return issues


def _validate_risk_levels(tasks: List[PrdTask]) -> List[PrdTaskValidationIssue]:
    """Check all tasks have valid risk levels."""
    issues: List[PrdTaskValidationIssue] = []
    for task in tasks:
        if task.risk_level not in VALID_RISK_LEVELS:
            issues.append(PrdTaskValidationIssue(
                issue_id=f"INVALID_RISK_{len(issues)+1:03d}",
                task_id=task.task_id,
                severity="blocker",
                message=f"Invalid risk_level {task.risk_level!r} on {task.task_id}",
                category="invalid_risk",
            ))
    return issues


def _validate_forbidden_statuses(tasks: List[PrdTask]) -> List[PrdTaskValidationIssue]:
    """Flag tasks with statuses that must not auto-execute."""
    issues: List[PrdTaskValidationIssue] = []
    for task in tasks:
        if task.status in _FORBIDDEN_AUTO_EXEC_STATUSES:
            issues.append(PrdTaskValidationIssue(
                issue_id=f"FORBIDDEN_STATUS_{len(issues)+1:03d}",
                task_id=task.task_id,
                severity="warning",
                message=(
                    f"Task {task.task_id} has status {task.status!r} — "
                    "must not auto-execute"
                ),
                category="forbidden_status",
            ))
    return issues


def _validate_contiguous(
    tasks: List[PrdTask],
    start_task_id: str,
    end_task_id: str,
) -> List[str]:
    """Return list of notes about gaps in the numeric sequence."""
    try:
        start_num = parse_task_number(start_task_id)
        end_num = parse_task_number(end_task_id)
    except ValueError:
        return []  # invalid IDs already caught

    present = set()
    for t in tasks:
        try:
            present.add(parse_task_number(t.task_id))
        except ValueError:
            pass

    notes: List[str] = []
    expected = set(range(start_num, end_num + 1))
    missing = sorted(expected - present)
    for m in missing:
        notes.append(f"Gap: T{m} expected in range but not in task list")
    return notes


def _compute_verdict(
    issues: List[PrdTaskValidationIssue],
    structural_invalid: bool,
) -> str:
    """Compute final verdict."""
    if structural_invalid:
        return "FAIL"
    blockers = sum(1 for i in issues if i.severity == "blocker")
    warnings = sum(1 for i in issues if i.severity == "warning")
    if blockers > 0:
        return "BLOCKED"
    if warnings > 0:
        return "WARN"
    return "PASS"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_prd_task_queue(
    tasks: List[PrdTask],
    start_task_id: str,
    end_task_id: str,
) -> PrdTaskQueueValidationReport:
    """Validate a PRD task queue range. Pure, deterministic, no I/O."""
    all_issues: List[PrdTaskValidationIssue] = []

    # Structural validity (invalid IDs -> FAIL)
    id_issues = _validate_task_ids(tasks)
    all_issues.extend(id_issues)
    structural_invalid = len(id_issues) > 0

    # Duplicate check
    all_issues.extend(_validate_no_duplicates(tasks))

    # Range presence
    all_issues.extend(_validate_range_present(tasks, start_task_id, end_task_id))

    # Range order
    all_issues.extend(_validate_range_order(start_task_id, end_task_id))

    # Status validity
    all_issues.extend(_validate_statuses(tasks))

    # Risk level validity
    all_issues.extend(_validate_risk_levels(tasks))

    # Forbidden auto-execute statuses
    all_issues.extend(_validate_forbidden_statuses(tasks))

    # Contiguity notes
    gap_notes = validate_task_range_contiguous(tasks, start_task_id, end_task_id)

    blockers = sum(1 for i in all_issues if i.severity == "blocker")
    warnings = sum(1 for i in all_issues if i.severity == "warning")

    return PrdTaskQueueValidationReport(
        total_tasks=len(tasks),
        issue_count=len(all_issues),
        blocker_count=blockers,
        warning_count=warnings,
        final_verdict=_compute_verdict(all_issues, structural_invalid),
        issues=tuple(all_issues),
        notes=tuple(gap_notes),
    )


def validate_task_range_contiguous(
    tasks: List[PrdTask],
    start_task_id: str,
    end_task_id: str,
) -> List[str]:
    """Check that all expected task IDs in range exist. Returns gap notes."""
    return _validate_contiguous(tasks, start_task_id, end_task_id)


def validation_report_to_dict(report: PrdTaskQueueValidationReport) -> Dict:
    """Serialize report to dict."""
    return {
        "total_tasks": report.total_tasks,
        "issue_count": report.issue_count,
        "blocker_count": report.blocker_count,
        "warning_count": report.warning_count,
        "final_verdict": report.final_verdict,
        "issues": [
            {
                "issue_id": i.issue_id,
                "task_id": i.task_id,
                "severity": i.severity,
                "message": i.message,
                "category": i.category,
            }
            for i in report.issues
        ],
        "notes": list(report.notes),
    }


def validation_report_to_markdown(report: PrdTaskQueueValidationReport) -> str:
    """Serialize report to deterministic markdown."""
    lines = [
        "# PRD Task Queue Validation Report",
        "",
        f"- **Total tasks:** {report.total_tasks}",
        f"- **Issues:** {report.issue_count}",
        f"- **Blockers:** {report.blocker_count}",
        f"- **Warnings:** {report.warning_count}",
        f"- **Verdict:** {report.final_verdict}",
    ]
    if report.issues:
        lines.append("")
        lines.append("| ID | Task | Severity | Category | Message |")
        lines.append("|-----|------|----------|----------|---------|")
        for i in report.issues:
            lines.append(
                f"| {i.issue_id} | {i.task_id} | {i.severity} | "
                f"{i.category} | {i.message} |"
            )
    if report.notes:
        lines.append("")
        lines.append("## Notes")
        for n in report.notes:
            lines.append(f"- {n}")
    return "\n".join(lines)
