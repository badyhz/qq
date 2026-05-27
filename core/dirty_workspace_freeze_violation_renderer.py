"""T1127 - Dirty Workspace Freeze Violation Renderer."""
from __future__ import annotations

from core.dirty_workspace_freeze_violation import DirtyWorkspaceFreezeViolation
from core.dirty_workspace_governance_verdict import DirtyWorkspaceGovernanceVerdict
from core.dirty_workspace_model_closeout import DirtyWorkspaceModelCloseout


def render_freeze_violation_md(violation: DirtyWorkspaceFreezeViolation) -> str:
    lines: list[str] = []
    lines.append("## Freeze Violation")
    lines.append("")
    lines.append(f"- **Violation ID:** {violation.violation_id}")
    lines.append(f"- **File Path:** {violation.file_path}")
    lines.append(f"- **Violation Type:** {violation.violation_type}")
    lines.append(f"- **Severity:** {violation.severity}")
    lines.append(f"- **Detected At Slot:** {violation.detected_at_slot}")
    lines.append("")
    return "\n".join(lines)


def render_governance_verdict_md(verdict: DirtyWorkspaceGovernanceVerdict) -> str:
    lines: list[str] = []
    lines.append("## Governance Verdict")
    lines.append("")
    lines.append(f"- **Verdict:** {verdict.verdict}")
    lines.append(f"- **Notes:** {verdict.notes}")
    lines.append("")
    if verdict.violations:
        lines.append("### Violations")
        for v in verdict.violations:
            lines.append(f"- [{v.severity}] {v.violation_type}: {v.file_path}")
        lines.append("")
    if verdict.duplicates:
        lines.append("### Duplicates")
        for d in verdict.duplicates:
            lines.append(f"- {d.canonical_path} -> {d.duplicate_path} [{d.action}]")
        lines.append("")
    return "\n".join(lines)


def render_closeout_md(closeout: DirtyWorkspaceModelCloseout) -> str:
    lines: list[str] = []
    lines.append("## Dirty Workspace Model Closeout")
    lines.append("")
    lines.append(f"- **Model Count:** {closeout.model_count}")
    lines.append(f"- **Verdict:** {closeout.verdict}")
    lines.append("")
    if closeout.models:
        lines.append("### Models")
        for model in closeout.models:
            lines.append(f"- {model}")
        lines.append("")
    return "\n".join(lines)
