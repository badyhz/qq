"""T1126 - Dirty Workspace Classification Renderer."""
from __future__ import annotations

from core.dirty_workspace_classification_result import DirtyWorkspaceClassificationResult
from core.dirty_workspace_file_record import DirtyWorkspaceFileRecord
from core.dirty_workspace_action_recommendation import DirtyWorkspaceActionRecommendation


def render_classification_result_md(result: DirtyWorkspaceClassificationResult) -> str:
    lines: list[str] = []
    lines.append("## Classification Result")
    lines.append("")
    lines.append(f"- **Total Files:** {result.total_files}")
    lines.append(f"- **High Risk:** {result.high_risk_count}")
    lines.append(f"- **Medium Risk:** {result.medium_risk_count}")
    lines.append(f"- **Low Risk:** {result.low_risk_count}")
    lines.append("")
    if result.records:
        lines.append("### File Records")
        for rec in result.records:
            lines.append(f"- **{rec.path}** [{rec.category}] risk={rec.risk_level} action={rec.action}")
        lines.append("")
    return "\n".join(lines)


def render_file_record_md(record: DirtyWorkspaceFileRecord) -> str:
    lines: list[str] = []
    lines.append("## File Record")
    lines.append("")
    lines.append(f"- **Path:** {record.path}")
    lines.append(f"- **Tracked:** {record.tracked}")
    lines.append(f"- **Category:** {record.category}")
    lines.append(f"- **Risk Level:** {record.risk_level}")
    lines.append(f"- **Action:** {record.action}")
    if record.notes:
        lines.append(f"- **Notes:** {record.notes}")
    lines.append("")
    return "\n".join(lines)


def render_action_recommendation_md(action: DirtyWorkspaceActionRecommendation) -> str:
    lines: list[str] = []
    lines.append("## Action Recommendations")
    lines.append("")
    for val in action.ALL_VALUES:
        lines.append(f"- {val}")
    lines.append("")
    return "\n".join(lines)
