"""PRD safety boundary checker — T870.

Pure, deterministic, no I/O, no timestamps, no random.
Checks proposed allowed files and task text against safety boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PrdSafetyBoundaryIssue:
    issue_id: str
    severity: str  # "blocker" | "warning"
    category: str
    target: str
    message: str


@dataclass(frozen=True)
class PrdSafetyBoundaryReport:
    checked_items: int
    issue_count: int
    blocker_count: int
    final_verdict: str  # PASS | WARN | BLOCKED
    issues: tuple  # tuple[PrdSafetyBoundaryIssue, ...]
    notes: tuple   # tuple[str, ...]


# ---------------------------------------------------------------------------
# Blocked path substrings (any match → BLOCKER)
# ---------------------------------------------------------------------------
_BLOCKED_PATH_SUBSTRINGS: tuple[str, ...] = (
    "scripts/submit",
    "live_runner",
    "exchange_client",
    "binance_testnet_client",
    "secrets",
    ".env",
    "credentials",
    "planner",
    "account",
    "order placement live path",
)


# ---------------------------------------------------------------------------
# Warning term substrings in task_text
# ---------------------------------------------------------------------------
_WARNING_TERMS: tuple[str, ...] = (
    "live trading",
    "real order",
    "submit",
    "API key",
    "secret",
    "exchange connection",
    "planner autonomous",
)


# ---------------------------------------------------------------------------
# Negation context words — if present near a warning term, suppress blocker
# ---------------------------------------------------------------------------
_NEGATION_WORDS: tuple[str, ...] = (
    "forbidden",
    "does not",
    "do not",
    "don't",
    "no ",
    "frozen",
    "never",
    "must not",
    "prohibited",
    "disallowed",
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_allowed_files(allowed_files: List[str]) -> List[PrdSafetyBoundaryIssue]:
    issues: List[PrdSafetyBoundaryIssue] = []
    for path in allowed_files:
        lower = path.lower()
        for substring in _BLOCKED_PATH_SUBSTRINGS:
            if substring in lower:
                issues.append(PrdSafetyBoundaryIssue(
                    issue_id=f"BLOCKED_PATH_{len(issues)+1:03d}",
                    severity="blocker",
                    category="blocked_path",
                    target=path,
                    message=f"File path contains forbidden substring '{substring}': {path}",
                ))
                break  # one issue per file
    return issues


def _has_negation_context(task_text: str, term: str) -> bool:
    """Return True if any negation word appears within ~80 chars of the term."""
    lower = task_text.lower()
    term_pos = lower.find(term.lower())
    if term_pos < 0:
        return False
    window = lower[max(0, term_pos - 80): term_pos + len(term) + 80]
    return any(neg in window for neg in _NEGATION_WORDS)


def _check_task_text(task_text: str) -> List[PrdSafetyBoundaryIssue]:
    issues: List[PrdSafetyBoundaryIssue] = []
    for term in _WARNING_TERMS:
        if term.lower() in task_text.lower():
            negated = _has_negation_context(task_text, term)
            severity = "warning" if negated else "blocker"
            category = "term_warning" if negated else "term_blocker"
            issues.append(PrdSafetyBoundaryIssue(
                issue_id=f"TERM_{len(issues)+1:03d}",
                severity=severity,
                category=category,
                target=term,
                message=f"Task text contains term '{term}'"
                        + (" (negation context detected)" if negated else ""),
            ))
    return issues


def _verdict(issues: List[PrdSafetyBoundaryIssue]) -> str:
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

def check_prd_safety_boundaries(
    task_text: str,
    allowed_files: List[str],
) -> PrdSafetyBoundaryReport:
    """Check task text and allowed files against safety boundaries."""
    issues = _check_allowed_files(allowed_files) + _check_task_text(task_text)
    blockers = sum(1 for i in issues if i.severity == "blocker")
    return PrdSafetyBoundaryReport(
        checked_items=len(allowed_files) + 1,
        issue_count=len(issues),
        blocker_count=blockers,
        final_verdict=_verdict(issues),
        issues=tuple(issues),
        notes=(),
    )


def safety_boundary_report_to_dict(report: PrdSafetyBoundaryReport) -> Dict:
    return {
        "checked_items": report.checked_items,
        "issue_count": report.issue_count,
        "blocker_count": report.blocker_count,
        "final_verdict": report.final_verdict,
        "issues": [
            {
                "issue_id": i.issue_id,
                "severity": i.severity,
                "category": i.category,
                "target": i.target,
                "message": i.message,
            }
            for i in report.issues
        ],
        "list": list(report.notes),
    }


def safety_boundary_report_to_markdown(report: PrdSafetyBoundaryReport) -> str:
    lines = [
        "# PRD Safety Boundary Report",
        "",
        f"- **Checked items:** {report.checked_items}",
        f"- **Issues:** {report.issue_count}",
        f"- **Blockers:** {report.blocker_count}",
        f"- **Verdict:** {report.final_verdict}",
    ]
    if report.issues:
        lines.append("")
        lines.append("| ID | Severity | Category | Target | Message |")
        lines.append("|-----|----------|----------|--------|---------|")
        for i in report.issues:
            lines.append(
                f"| {i.issue_id} | {i.severity} | {i.category} | {i.target} | {i.message} |"
            )
    if report.notes:
        lines.append("")
        lines.append("## Notes")
        for n in report.notes:
            lines.append(f"- {n}")
    return "\n".join(lines)
