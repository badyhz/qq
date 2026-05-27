"""Governance failure regression packet — combines taxonomy, report, snapshot.

No file I/O. No network. Pure composition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.governance_failure_taxonomy import GovernanceFailure, summarize_failures
from core.governance_failure_report import (
    GovernanceFailureReport,
    build_governance_failure_report,
    report_to_dict,
    report_to_markdown,
)
from core.governance_failure_snapshot import (
    GovernanceFailureSnapshotDiff,
    compare_governance_failure_markdown,
)


@dataclass
class GovernanceFailureRegressionPacket:
    report: GovernanceFailureReport
    snapshot_diff: GovernanceFailureSnapshotDiff
    report_summary: Dict[str, Any]
    snapshot_summary: Dict[str, Any]
    final_verdict: str
    notes: List[str]


def build_governance_failure_regression_packet(
    failures: List[GovernanceFailure],
    *,
    title: str = "Governance Failure Regression",
    expected_markdown: str | None = None,
    notes: List[str] | None = None,
) -> GovernanceFailureRegressionPacket:
    """Build a regression packet from failures and optional snapshot.

    Pure. Deterministic. No I/O.
    """
    report = build_governance_failure_report(failures, title=title)

    actual_markdown = report_to_markdown(report)

    if expected_markdown is not None:
        snapshot_diff = compare_governance_failure_markdown(expected_markdown, actual_markdown)
    else:
        snapshot_diff = GovernanceFailureSnapshotDiff(
            ok=True,
            expected_hash="",
            actual_hash="",
            changed_sections=[],
            added_lines=[],
            removed_lines=[],
        )

    report_summary = {
        "verdict": report.verdict,
        "total_failures": report.total_failures,
        "retryable_count": report.retryable_count,
        "critical_count": report.critical_count,
    }

    snapshot_summary = {
        "ok": snapshot_diff.ok,
        "expected_hash": snapshot_diff.expected_hash,
        "actual_hash": snapshot_diff.actual_hash,
        "changed_sections": list(snapshot_diff.changed_sections),
    }

    final_verdict = _compute_final_verdict(report.verdict, snapshot_diff.ok)

    return GovernanceFailureRegressionPacket(
        report=report,
        snapshot_diff=snapshot_diff,
        report_summary=report_summary,
        snapshot_summary=snapshot_summary,
        final_verdict=final_verdict,
        notes=list(notes) if notes else [],
    )


def packet_to_dict(packet: GovernanceFailureRegressionPacket) -> Dict[str, Any]:
    """Serialize packet to plain dict. Deterministic."""
    return {
        "report": report_to_dict(packet.report),
        "snapshot_diff": {
            "ok": packet.snapshot_diff.ok,
            "expected_hash": packet.snapshot_diff.expected_hash,
            "actual_hash": packet.snapshot_diff.actual_hash,
            "changed_sections": list(packet.snapshot_diff.changed_sections),
            "added_lines": list(packet.snapshot_diff.added_lines),
            "removed_lines": list(packet.snapshot_diff.removed_lines),
        },
        "report_summary": dict(packet.report_summary),
        "snapshot_summary": dict(packet.snapshot_summary),
        "final_verdict": packet.final_verdict,
        "notes": list(packet.notes),
    }


def packet_to_markdown(packet: GovernanceFailureRegressionPacket) -> str:
    """Render packet as deterministic markdown."""
    lines: List[str] = []

    lines.append(f"# {packet.report.title}")
    lines.append("")

    lines.append(f"**Final Verdict:** {packet.final_verdict}")
    lines.append(f"**Report Verdict:** {packet.report_summary['verdict']}")
    lines.append(f"**Snapshot OK:** {packet.snapshot_diff.ok}")
    lines.append("")

    # snapshot diff
    lines.append("## Snapshot Diff")
    lines.append("")
    lines.append(f"- **OK:** {packet.snapshot_diff.ok}")
    if packet.snapshot_diff.expected_hash:
        lines.append(f"- **Expected hash:** {packet.snapshot_diff.expected_hash}")
    if packet.snapshot_diff.actual_hash:
        lines.append(f"- **Actual hash:** {packet.snapshot_diff.actual_hash}")
    if packet.snapshot_diff.changed_sections:
        lines.append(f"- **Changed sections:** {', '.join(packet.snapshot_diff.changed_sections)}")
    if packet.snapshot_diff.added_lines:
        lines.append(f"- **Added lines:** {len(packet.snapshot_diff.added_lines)}")
    if packet.snapshot_diff.removed_lines:
        lines.append(f"- **Removed lines:** {len(packet.snapshot_diff.removed_lines)}")
    lines.append("")

    # report summary
    lines.append("## Report Summary")
    lines.append("")
    lines.append(f"- **Total failures:** {packet.report_summary['total_failures']}")
    lines.append(f"- **Retryable:** {packet.report_summary['retryable_count']}")
    lines.append(f"- **Critical:** {packet.report_summary['critical_count']}")
    lines.append("")

    # by category
    if packet.report.by_category:
        lines.append("## By Category")
        lines.append("")
        lines.append("| Category | Count |")
        lines.append("|----------|-------|")
        for cat in sorted(packet.report.by_category.keys()):
            lines.append(f"| {cat} | {packet.report.by_category[cat]} |")
        lines.append("")

    # by severity
    if packet.report.by_severity:
        lines.append("## By Severity")
        lines.append("")
        lines.append("| Severity | Count |")
        lines.append("|----------|-------|")
        for sev in sorted(packet.report.by_severity.keys()):
            lines.append(f"| {sev} | {packet.report.by_severity[sev]} |")
        lines.append("")

    # notes
    if packet.notes:
        lines.append("## Notes")
        lines.append("")
        for note in packet.notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)


def _compute_final_verdict(report_verdict: str, snapshot_ok: bool) -> str:
    """Combine report verdict and snapshot status."""
    if not snapshot_ok:
        if report_verdict == "BLOCKED":
            return "BLOCKED"
        return "FAIL"
    return report_verdict
