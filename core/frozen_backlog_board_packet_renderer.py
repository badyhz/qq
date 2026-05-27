"""T1853 - Frozen Backlog Board Packet Renderer.

Pure function that produces a combined markdown document with all key
governance info for board review. No I/O. No timestamps. No network.
"""
from __future__ import annotations

from core.frozen_backlog_report_record import FrozenBacklogReportRecord
from core.frozen_backlog_report_summary import FrozenBacklogReportSummary
from core.frozen_backlog_validation_result import FrozenBacklogValidationResult


def render_board_packet_md(
    summary: FrozenBacklogReportSummary,
    records: tuple[FrozenBacklogReportRecord, ...],
    validation_result: FrozenBacklogValidationResult,
) -> str:
    """Render combined board packet markdown.

    Pure function. No I/O. No timestamps. No network.
    """
    lines: list[str] = []

    # Header
    lines.append("# Frozen Backlog Review — Board Packet")
    lines.append("")
    lines.append(f"**Release Hold:** {summary.release_hold}")
    lines.append("")

    # Summary section
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- **Total Frozen Files:** {summary.total_files}")
    lines.append(f"- **High Risk Files:** {summary.high_risk_count}")
    lines.append(f"- **Medium Risk Files:** {summary.medium_risk_count}")
    lines.append("")

    # Safety constraints
    lines.append("## Safety Constraints")
    lines.append("")
    lines.append(f"- No Live: {summary.no_live}")
    lines.append(f"- No Submit: {summary.no_submit}")
    lines.append(f"- No Exchange: {summary.no_exchange}")
    lines.append(f"- No Runtime Integration: {summary.no_runtime_integration}")
    lines.append(f"- No Planner Integration: {summary.no_planner_integration}")
    lines.append("")

    # Validation status
    lines.append("## Validation Status")
    lines.append("")
    val_status = "PASS" if validation_result.is_valid else "FAIL"
    lines.append(f"- **Status:** {val_status}")
    lines.append(
        f"- **Checks Passed:** {len(validation_result.checks_passed)}"
    )
    lines.append(
        f"- **Checks Failed:** {len(validation_result.checks_failed)}"
    )
    if validation_result.error_message:
        lines.append(
            f"- **Error:** {validation_result.error_message}"
        )
    lines.append("")

    # File inventory table
    lines.append("## File Inventory")
    lines.append("")
    lines.append(
        "| # | File | Risk | Category | Readiness | Unlock |"
    )
    lines.append(
        "|---|------|------|----------|-----------|--------|"
    )
    for idx, rec in enumerate(records):
        lines.append(
            f"| {idx + 1} | {rec.file_path} | {rec.risk_class} "
            f"| {rec.category} | {rec.readiness_score:.1f} "
            f"| {rec.unlock_recommendation} |"
        )
    lines.append("")

    # Action matrix
    lines.append("## Action Matrix")
    lines.append("")
    for rec in records:
        allowed = ", ".join(rec.allowed_actions)
        forbidden = ", ".join(rec.forbidden_actions)
        lines.append(f"### {rec.file_path}")
        lines.append(f"- **Allowed:** {allowed}")
        lines.append(f"- **Forbidden:** {forbidden}")
        lines.append("")

    # Required evidence summary
    lines.append("## Required Evidence by Risk Class")
    lines.append("")
    high_evidence: set[str] = set()
    med_evidence: set[str] = set()
    for rec in records:
        if rec.risk_class == "HIGH":
            high_evidence.update(rec.required_evidence)
        else:
            med_evidence.update(rec.required_evidence)
    lines.append("**HIGH risk files require:**")
    for ev in sorted(high_evidence):
        lines.append(f"- {ev}")
    lines.append("")
    lines.append("**MEDIUM risk files require:**")
    for ev in sorted(med_evidence):
        lines.append(f"- {ev}")
    lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(
        "Frozen Backlog Review Platform v1 — Board Packet. "
        "release_hold=HOLD enforced. No live, no submit, no exchange."
    )

    return "\n".join(lines)
