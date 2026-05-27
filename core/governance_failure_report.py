"""Governance failure report — pure reporting layer.

Converts GovernanceFailure objects into deterministic dict/markdown reports.
No network. No file I/O. No live system dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.governance_failure_taxonomy import (
    FailureCategory,
    FailureSeverity,
    GovernanceFailure,
    summarize_failures,
)


@dataclass
class GovernanceFailureReport:
    title: str
    total_failures: int
    by_category: Dict[str, int]
    by_severity: Dict[str, int]
    retryable_count: int
    non_retryable_count: int
    critical_count: int
    top_sources: List[tuple[str, int]]
    failures: List[Dict[str, Any]]
    verdict: str
    notes: List[str]


# ── builder ──────────────────────────────────────────────────────────


def build_governance_failure_report(
    failures: List[GovernanceFailure],
    title: str = "Governance Failure Report",
    notes: List[str] | None = None,
) -> GovernanceFailureReport:
    """Build a report from a list of GovernanceFailure. Pure, deterministic."""
    summary = summarize_failures(failures)

    critical_count = sum(
        1 for f in failures if f.severity == FailureSeverity.CRITICAL
    )

    # top sources: count by source, sort desc by count, then asc by name
    source_counts: Dict[str, int] = {}
    for f in failures:
        if f.source:
            source_counts[f.source] = source_counts.get(f.source, 0) + 1
    top_sources = sorted(source_counts.items(), key=lambda x: (-x[1], x[0]))

    # serialize failures in order
    from core.governance_failure_taxonomy import failure_to_dict

    failure_dicts = [failure_to_dict(f) for f in failures]

    verdict = _compute_verdict(failures, critical_count)

    return GovernanceFailureReport(
        title=title,
        total_failures=summary["total"],
        by_category=summary["by_category"],
        by_severity=summary["by_severity"],
        retryable_count=summary["retryable"],
        non_retryable_count=summary["non_retryable"],
        critical_count=critical_count,
        top_sources=top_sources,
        failures=failure_dicts,
        verdict=verdict,
        notes=list(notes) if notes else [],
    )


# ── serialization ────────────────────────────────────────────────────


def report_to_dict(report: GovernanceFailureReport) -> Dict[str, Any]:
    """Serialize report to a plain dict. Deterministic."""
    return {
        "title": report.title,
        "total_failures": report.total_failures,
        "by_category": dict(sorted(report.by_category.items())),
        "by_severity": dict(sorted(report.by_severity.items())),
        "retryable_count": report.retryable_count,
        "non_retryable_count": report.non_retryable_count,
        "critical_count": report.critical_count,
        "top_sources": [{"source": s, "count": c} for s, c in report.top_sources],
        "failures": report.failures,
        "verdict": report.verdict,
        "notes": list(report.notes),
    }


# ── markdown ─────────────────────────────────────────────────────────


def report_to_markdown(report: GovernanceFailureReport) -> str:
    """Render report as deterministic markdown. Stable ordering, no timestamps."""
    lines: List[str] = []

    lines.append(f"# {report.title}")
    lines.append("")

    lines.append(f"**Verdict:** {report.verdict}")
    lines.append(f"**Total failures:** {report.total_failures}")
    lines.append(f"**Retryable:** {report.retryable_count} / **Non-retryable:** {report.non_retryable_count}")
    lines.append(f"**Critical:** {report.critical_count}")
    lines.append("")

    # by category (sorted)
    if report.by_category:
        lines.append("## By Category")
        lines.append("")
        lines.append("| Category | Count |")
        lines.append("|----------|-------|")
        for cat in sorted(report.by_category.keys()):
            lines.append(f"| {cat} | {report.by_category[cat]} |")
        lines.append("")

    # by severity (sorted)
    if report.by_severity:
        lines.append("## By Severity")
        lines.append("")
        lines.append("| Severity | Count |")
        lines.append("|----------|-------|")
        for sev in sorted(report.by_severity.keys()):
            lines.append(f"| {sev} | {report.by_severity[sev]} |")
        lines.append("")

    # top sources
    if report.top_sources:
        lines.append("## Top Sources")
        lines.append("")
        lines.append("| Source | Count |")
        lines.append("|--------|-------|")
        for source, count in report.top_sources:
            lines.append(f"| {source} | {count} |")
        lines.append("")

    # failure details
    if report.failures:
        lines.append("## Failures")
        lines.append("")
        for i, f in enumerate(report.failures, 1):
            lines.append(f"### {i}. {f['code']}")
            lines.append("")
            lines.append(f"- **Category:** {f['category']}")
            lines.append(f"- **Severity:** {f['severity']}")
            lines.append(f"- **Message:** {f['message']}")
            if f["source"]:
                lines.append(f"- **Source:** {f['source']}")
            lines.append(f"- **Retryable:** {f['retryable']}")
            if f["metadata"]:
                for mk in sorted(f["metadata"].keys()):
                    lines.append(f"- **{mk}:** {f['metadata'][mk]}")
            lines.append("")

    # notes
    if report.notes:
        lines.append("## Notes")
        lines.append("")
        for note in report.notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)


# ── internal ─────────────────────────────────────────────────────────


def _compute_verdict(
    failures: List[GovernanceFailure],
    critical_count: int,
) -> str:
    if not failures:
        return "PASS"
    if critical_count > 0:
        has_critical_non_retryable = any(
            f.severity == FailureSeverity.CRITICAL and not f.retryable
            for f in failures
        )
        if has_critical_non_retryable:
            return "BLOCKED"
    has_error = any(f.severity == FailureSeverity.ERROR for f in failures)
    if has_error or critical_count > 0:
        return "FAIL"
    return "WARN"
