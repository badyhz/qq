"""PRD 500 backlog validator — deterministic validation for 500+ task backlogs.

T904. Pure deterministic, no I/O, no timestamps, no random.
"""

from dataclasses import dataclass
from typing import Dict, List

from core.prd_backlog_schema import PrdBacklog

# --- Dataclasses ---


@dataclass(frozen=True)
class Prd500BacklogValidationIssue:
    issue_id: str
    severity: str  # "warning", "blocker", "fail"
    task_id: str
    category: str
    message: str


@dataclass(frozen=True)
class Prd500BacklogValidationReport:
    total_items: int
    issue_count: int
    blocker_count: int
    warning_count: int
    final_verdict: str  # PASS, WARN, BLOCKED, FAIL
    issues: List[Prd500BacklogValidationIssue]
    notes: List[str]


# --- Constants ---

_EXECUTABLE_STATUSES = frozenset({"NOT_STARTED", "COMPLETED", "IN_PROGRESS"})
_HIGH_RISK_LEVELS = frozenset({"HIGH"})
_FROZEN_RISK = "FROZEN"

_REQUIRED_FORBIDDEN_PATTERNS = frozenset({
    ".env",
    "credentials",
    "secrets",
})

_UNSAFE_FROZEN_PATTERNS = frozenset({
    "main.py",
    "config.yaml",
})


# --- Validation ---


def validate_prd_500_backlog(backlog: PrdBacklog) -> Prd500BacklogValidationReport:
    """Validate a PRD backlog against the 500-backlog rules.

    Rules:
    - PASS: items >= 500, no duplicates, no unsafe frozen, no live auth,
      forbidden patterns present.
    - WARN: high risk tasks exist but human review present.
    - BLOCKED: frozen tasks have executable status
      (NOT_STARTED / COMPLETED / IN_PROGRESS).
    - FAIL: items < 500 or duplicate task_ids.
    """
    issues: List[Prd500BacklogValidationIssue] = []
    notes: List[str] = []
    issue_seq = 0

    def _next_issue_id() -> str:
        nonlocal issue_seq
        issue_seq += 1
        return f"V500-{issue_seq:04d}"

    # --- Duplicate check ---
    seen_ids: Dict[str, int] = {}
    for idx, item in enumerate(backlog.items):
        if item.task_id in seen_ids:
            issues.append(Prd500BacklogValidationIssue(
                issue_id=_next_issue_id(),
                severity="fail",
                task_id=item.task_id,
                category="duplicate",
                message=f"Duplicate task_id {item.task_id!r} at indices {seen_ids[item.task_id]} and {idx}",
            ))
        else:
            seen_ids[item.task_id] = idx

    # --- Count check ---
    total_items = len(backlog.items)
    if total_items < 500:
        issues.append(Prd500BacklogValidationIssue(
            issue_id=_next_issue_id(),
            severity="fail",
            task_id="*",
            category="count",
            message=f"Backlog has {total_items} items, minimum required is 500",
        ))

    # --- Frozen executable check ---
    for item in backlog.items:
        if item.risk_level == _FROZEN_RISK and item.status in _EXECUTABLE_STATUSES:
            issues.append(Prd500BacklogValidationIssue(
                issue_id=_next_issue_id(),
                severity="blocker",
                task_id=item.task_id,
                category="frozen_executable",
                message=(
                    f"FROZEN task {item.task_id} has executable status "
                    f"{item.status!r}; frozen tasks must be BLOCKED or HUMAN_REVIEW_REQUIRED"
                ),
            ))

    # --- Unsafe frozen file patterns ---
    for item in backlog.items:
        if item.risk_level == _FROZEN_RISK:
            all_patterns = set(item.allowed_file_patterns) | set(item.forbidden_file_patterns)
            for unsafe in _UNSAFE_FROZEN_PATTERNS:
                if unsafe in item.allowed_file_patterns:
                    issues.append(Prd500BacklogValidationIssue(
                        issue_id=_next_issue_id(),
                        severity="blocker",
                        task_id=item.task_id,
                        category="unsafe_frozen",
                        message=f"FROZEN task {item.task_id} allows unsafe pattern {unsafe!r}",
                    ))

    # --- Live auth check ---
    _LIVE_AUTH_PHRASES = [
        "authorized for live",
        "authorized for real order",
        "live trading authorized",
        "live execution authorized",
    ]
    for item in backlog.items:
        for note in item.notes:
            note_lower = note.lower()
            for phrase in _LIVE_AUTH_PHRASES:
                if phrase in note_lower:
                    issues.append(Prd500BacklogValidationIssue(
                        issue_id=_next_issue_id(),
                        severity="blocker",
                        task_id=item.task_id,
                        category="live_auth",
                        message=f"Task {item.task_id} contains unauthorized claim: {phrase!r}",
                    ))

    # --- Forbidden patterns check ---
    has_forbidden = False
    for item in backlog.items:
        if item.forbidden_file_patterns:
            has_forbidden = True
            break
    if not has_forbidden:
        issues.append(Prd500BacklogValidationIssue(
            issue_id=_next_issue_id(),
            severity="warning",
            task_id="*",
            category="missing_forbidden",
            message="No items have forbidden_file_patterns defined",
        ))

    # --- High risk + human review ---
    for item in backlog.items:
        if item.risk_level in _HIGH_RISK_LEVELS:
            if item.status == "HUMAN_REVIEW_REQUIRED":
                notes.append(f"HIGH risk task {item.task_id} has human review — acceptable")
            else:
                issues.append(Prd500BacklogValidationIssue(
                    issue_id=_next_issue_id(),
                    severity="warning",
                    task_id=item.task_id,
                    category="high_risk_no_review",
                    message=f"HIGH risk task {item.task_id} has status {item.status!r}, expected HUMAN_REVIEW_REQUIRED",
                ))

    # --- Compute verdict ---
    blocker_count = sum(1 for i in issues if i.severity == "blocker")
    warning_count = sum(1 for i in issues if i.severity == "warning")
    fail_count = sum(1 for i in issues if i.severity == "fail")

    if fail_count > 0:
        verdict = "FAIL"
    elif blocker_count > 0:
        verdict = "BLOCKED"
    elif warning_count > 0:
        verdict = "WARN"
    else:
        verdict = "PASS"

    return Prd500BacklogValidationReport(
        total_items=total_items,
        issue_count=len(issues),
        blocker_count=blocker_count,
        warning_count=warning_count,
        final_verdict=verdict,
        issues=tuple(issues),
        notes=tuple(notes),
    )


# --- Serializers ---


def validation_report_to_dict(report: Prd500BacklogValidationReport) -> Dict:
    """Convert validation report to plain dict."""
    return {
        "total_items": report.total_items,
        "issue_count": report.issue_count,
        "blocker_count": report.blocker_count,
        "warning_count": report.warning_count,
        "final_verdict": report.final_verdict,
        "issues": [
            {
                "issue_id": i.issue_id,
                "severity": i.severity,
                "task_id": i.task_id,
                "category": i.category,
                "message": i.message,
            }
            for i in report.issues
        ],
        "notes": list(report.notes),
    }


def validation_report_to_markdown(report: Prd500BacklogValidationReport) -> str:
    """Convert validation report to markdown string."""
    lines: List[str] = []
    lines.append("# PRD 500 Backlog Validation Report")
    lines.append("")
    lines.append(f"- **Total items:** {report.total_items}")
    lines.append(f"- **Issues:** {report.issue_count}")
    lines.append(f"- **Blockers:** {report.blocker_count}")
    lines.append(f"- **Warnings:** {report.warning_count}")
    lines.append(f"- **Verdict:** {report.final_verdict}")
    lines.append("")
    if report.issues:
        lines.append("## Issues")
        lines.append("")
        for issue in report.issues:
            lines.append(
                f"- [{issue.severity.upper()}] `{issue.issue_id}` "
                f"({issue.category}) `{issue.task_id}`: {issue.message}"
            )
        lines.append("")
    if report.notes:
        lines.append("## Notes")
        lines.append("")
        for note in report.notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)
