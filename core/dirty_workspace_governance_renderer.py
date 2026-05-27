"""T1125 - Dirty Workspace Governance Renderer."""
from __future__ import annotations

from core.dirty_workspace_governance import DirtyWorkspaceGovernance
from core.dirty_workspace_file_category import DirtyWorkspaceFileCategory
from core.dirty_workspace_risk_level import DirtyWorkspaceRiskLevel


def render_dirty_workspace_governance_md(gov: DirtyWorkspaceGovernance) -> str:
    lines: list[str] = []
    lines.append("## Dirty Workspace Governance")
    lines.append("")
    lines.append(f"- **Policy Version:** {gov.policy_version}")
    lines.append(f"- **Enforcement Mode:** {gov.enforcement_mode}")
    lines.append("")
    if gov.file_categories:
        lines.append("### File Categories")
        for cat in gov.file_categories:
            lines.append(f"- {cat}")
        lines.append("")
    if gov.risk_levels:
        lines.append("### Risk Levels")
        for level in gov.risk_levels:
            lines.append(f"- {level}")
        lines.append("")
    return "\n".join(lines)


def render_file_category_md(cat: DirtyWorkspaceFileCategory) -> str:
    lines: list[str] = []
    lines.append("## File Categories")
    lines.append("")
    for name in cat.ALL_VALUES:
        lines.append(f"- {name}")
    lines.append("")
    return "\n".join(lines)


def render_risk_level_md(level: DirtyWorkspaceRiskLevel) -> str:
    lines: list[str] = []
    lines.append("## Risk Levels")
    lines.append("")
    for val in level.ALL_VALUES:
        lines.append(f"- {val}")
    lines.append("")
    return "\n".join(lines)
