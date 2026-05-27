"""T1128 - Dirty Workspace Duplicate Report Renderer."""
from __future__ import annotations

from core.dirty_workspace_duplicate_record import DirtyWorkspaceDuplicateRecord


def render_duplicate_record_md(record: DirtyWorkspaceDuplicateRecord) -> str:
    lines: list[str] = []
    lines.append("## Duplicate Record")
    lines.append("")
    lines.append(f"- **Canonical Path:** {record.canonical_path}")
    lines.append(f"- **Duplicate Path:** {record.duplicate_path}")
    lines.append(f"- **Category:** {record.category}")
    lines.append(f"- **Action:** {record.action}")
    lines.append("")
    return "\n".join(lines)


def render_duplicate_summary_md(records: tuple) -> str:
    lines: list[str] = []
    lines.append("## Duplicate Summary")
    lines.append("")
    lines.append(f"- **Total Duplicates:** {len(records)}")
    lines.append("")
    if records:
        lines.append("### Records")
        for rec in records:
            lines.append(f"- {rec.canonical_path} == {rec.duplicate_path} [{rec.category}] {rec.action}")
        lines.append("")
    return "\n".join(lines)
