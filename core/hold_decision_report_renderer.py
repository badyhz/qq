"""T1464 - Hold decision report markdown renderer. Pure functions."""
from __future__ import annotations

from core.hold_decision_report import HoldDecisionReport


def render_hold_decision_report_md(report: HoldDecisionReport) -> str:
    """Render HoldDecisionReport to markdown."""
    lines: list[str] = []
    lines.append("## Hold Decision Report")
    lines.append("")
    lines.append(f"- **ID:** {report.report_id}")
    lines.append(f"- **File:** {report.file_path}")
    lines.append(f"- **Risk Class:** {report.risk_class}")
    lines.append(f"- **Readiness Score:** {report.readiness_score:.2f}")
    lines.append(f"- **Unlock Recommendation:** {report.unlock_recommendation}")
    lines.append("")
    lines.append(render_hold_status_md(report))
    lines.append(render_human_decision_md(report))
    if report.required_evidence:
        lines.append("### Required Evidence")
        lines.append("")
        for e in report.required_evidence:
            lines.append(f"- {e}")
        lines.append("")
    return "\n".join(lines)


def render_hold_status_md(report: HoldDecisionReport) -> str:
    """Render hold status section."""
    lines: list[str] = []
    lines.append("### Hold Status")
    lines.append("")
    lines.append(f"- **Status:** {report.current_hold_status}")
    lines.append("")
    return "\n".join(lines)


def render_human_decision_md(report: HoldDecisionReport) -> str:
    """Render human decision section."""
    lines: list[str] = []
    lines.append("### Human Decision")
    lines.append("")
    lines.append(f"- **Decision:** {report.human_decision}")
    if report.decision_rationale:
        lines.append(f"- **Rationale:** {report.decision_rationale}")
    lines.append("")
    return "\n".join(lines)
