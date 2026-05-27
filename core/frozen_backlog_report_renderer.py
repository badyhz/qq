"""T1528 - Frozen Backlog Report Markdown Renderer.

Pure functions. No I/O. No timestamps. No network.
"""
from __future__ import annotations

from core.frozen_backlog_report_record import FrozenBacklogReportRecord
from core.frozen_backlog_report_summary import FrozenBacklogReportSummary


def render_record_markdown(record: FrozenBacklogReportRecord) -> str:
    """Render a single FrozenBacklogReportRecord to markdown."""
    lines: list[str] = []
    lines.append(f"### {record.file_path}")
    lines.append("")
    lines.append(f"- **Record ID:** {record.record_id}")
    lines.append(f"- **Risk Class:** {record.risk_class}")
    lines.append(f"- **Category:** {record.category}")
    lines.append(f"- **Release Hold:** {record.release_hold}")
    lines.append(f"- **Readiness Score:** {record.readiness_score}")
    lines.append(f"- **Unlock Recommendation:** {record.unlock_recommendation}")
    lines.append("")
    if record.allowed_actions:
        lines.append("**Allowed Actions:**")
        for action in record.allowed_actions:
            lines.append(f"- {action}")
        lines.append("")
    if record.forbidden_actions:
        lines.append("**Forbidden Actions:**")
        for action in record.forbidden_actions:
            lines.append(f"- {action}")
        lines.append("")
    if record.required_evidence:
        lines.append("**Required Evidence:**")
        for evidence in record.required_evidence:
            lines.append(f"- {evidence}")
        lines.append("")
    return "\n".join(lines)


def render_summary_markdown(summary: FrozenBacklogReportSummary) -> str:
    """Render FrozenBacklogReportSummary to markdown."""
    lines: list[str] = []
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Summary ID:** {summary.summary_id}")
    lines.append(f"- **Total Files:** {summary.total_files}")
    lines.append(f"- **High Risk Count:** {summary.high_risk_count}")
    lines.append(f"- **Medium Risk Count:** {summary.medium_risk_count}")
    lines.append(f"- **Release Hold:** {summary.release_hold}")
    lines.append("")
    lines.append("### Safety Constraints")
    lines.append("")
    lines.append(f"- **No Live:** {summary.no_live}")
    lines.append(f"- **No Submit:** {summary.no_submit}")
    lines.append(f"- **No Exchange:** {summary.no_exchange}")
    lines.append(f"- **No Runtime Integration:** {summary.no_runtime_integration}")
    lines.append(f"- **No Planner Integration:** {summary.no_planner_integration}")
    lines.append("")
    return "\n".join(lines)


def render_report_markdown(
    summary: FrozenBacklogReportSummary,
    records: tuple[FrozenBacklogReportRecord, ...],
) -> str:
    """Generate full markdown report with header, summary, per-file sections."""
    lines: list[str] = []
    lines.append("# Frozen Backlog Review Report")
    lines.append("")
    lines.append(f"**Release Hold:** {summary.release_hold}")
    lines.append("")
    lines.append(render_summary_markdown(summary))
    lines.append("## Frozen Files")
    lines.append("")
    for record in records:
        lines.append(render_record_markdown(record))
        lines.append("---")
        lines.append("")
    return "\n".join(lines)
