"""T1616 - Frozen Backlog Diff Markdown Renderer.

Pure functions for rendering diffs and verdicts to markdown.
No I/O. No timestamps. No network.
"""
from __future__ import annotations

from core.frozen_backlog_diff import FrozenBacklogDiff
from core.frozen_backlog_verdict import FrozenBacklogVerdict
from core.frozen_diff_change import FrozenDiffChange


def render_change_md(change: FrozenDiffChange) -> str:
    """Render a single FrozenDiffChange to markdown. Pure function."""
    return (
        f"- **{change.file_path}** — `{change.field_name}`: "
        f"`{change.old_value}` → `{change.new_value}`"
    )


def render_diff_md(diff: FrozenBacklogDiff) -> str:
    """Render a FrozenBacklogDiff to markdown. Pure function."""
    lines: list[str] = []
    lines.append(f"## Diff: {diff.diff_id}")
    lines.append("")
    lines.append(f"- **Before:** {diff.before_snapshot_id}")
    lines.append(f"- **After:** {diff.after_snapshot_id}")
    lines.append("")

    if diff.added_files:
        lines.append("### Added Files")
        for f in diff.added_files:
            lines.append(f"- `{f}`")
        lines.append("")

    if diff.removed_files:
        lines.append("### Removed Files")
        for f in diff.removed_files:
            lines.append(f"- `{f}`")
        lines.append("")

    for section_name, changes in [
        ("Risk Class Changes", diff.risk_class_changes),
        ("Category Changes", diff.category_changes),
        ("Recommendation Changes", diff.recommendation_changes),
        ("Safety Flag Changes", diff.safety_flag_changes),
        ("Hold Changes", diff.hold_changes),
    ]:
        if changes:
            lines.append(f"### {section_name}")
            for change in changes:
                lines.append(render_change_md(change))
            lines.append("")

    if not (
        diff.added_files
        or diff.removed_files
        or diff.risk_class_changes
        or diff.category_changes
        or diff.recommendation_changes
        or diff.safety_flag_changes
        or diff.hold_changes
    ):
        lines.append("*No changes detected.*")
        lines.append("")

    return "\n".join(lines)


def render_verdict_md(verdict: FrozenBacklogVerdict) -> str:
    """Render a FrozenBacklogVerdict to markdown. Pure function."""
    lines: list[str] = []
    lines.append("## Verdict")
    lines.append("")
    lines.append(f"- **Result:** {verdict.verdict}")
    lines.append(f"- **Risk Level:** {verdict.risk_level}")
    lines.append(f"- **Notes:** {verdict.notes}")
    if verdict.changed_fields:
        lines.append("- **Changed Fields:**")
        for field in verdict.changed_fields:
            lines.append(f"  - `{field}`")
    lines.append("")
    return "\n".join(lines)
