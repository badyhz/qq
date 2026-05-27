"""PRD backlog rich markdown renderer — T890.

Pure deterministic, no I/O, no timestamps, no random.
Renders PrdBacklog into comprehensive or summary markdown documents.
"""

from typing import Dict, List

from core.prd_backlog_schema import PrdBacklog, PrdBacklogItem, summarize_backlog


# --- Helpers ---


def _render_status_table(status_counts: Dict[str, int]) -> str:
    """Render status counts as a markdown table. Keys sorted alphabetically."""
    lines: List[str] = []
    lines.append("| Status | Count |")
    lines.append("|--------|-------|")
    for key in sorted(status_counts):
        lines.append(f"| {key} | {status_counts[key]} |")
    return "\n".join(lines)


def _render_risk_table(risk_counts: Dict[str, int]) -> str:
    """Render risk counts as a markdown table. Keys sorted alphabetically."""
    lines: List[str] = []
    lines.append("| Risk Level | Count |")
    lines.append("|------------|-------|")
    for key in sorted(risk_counts):
        lines.append(f"| {key} | {risk_counts[key]} |")
    return "\n".join(lines)


def _render_item_detail(item: PrdBacklogItem) -> str:
    """Render a single backlog item as markdown."""
    lines: List[str] = []
    lines.append(f"### {item.task_id}: {item.title}")
    lines.append("")
    lines.append(f"- **Wave:** {item.wave_id}")
    lines.append(f"- **Batch:** {item.batch_id}")
    lines.append(f"- **Status:** {item.status}")
    lines.append(f"- **Risk:** {item.risk_level}")
    if item.dependencies:
        lines.append(f"- **Dependencies:** {', '.join(item.dependencies)}")
    if item.allowed_file_patterns:
        lines.append(f"- **Allowed file patterns:** {', '.join(item.allowed_file_patterns)}")
    if item.forbidden_file_patterns:
        lines.append(f"- **Forbidden file patterns:** {', '.join(item.forbidden_file_patterns)}")
    if item.acceptance_command_ids:
        lines.append("- **Acceptance commands:**")
        for cmd_id in item.acceptance_command_ids:
            lines.append(f"  - `{cmd_id}`")
    if item.notes:
        lines.append("- **Notes:**")
        for note in item.notes:
            lines.append(f"  - {note}")
    lines.append("")
    return "\n".join(lines)


# --- Public API ---


def render_backlog_full_markdown(backlog: PrdBacklog) -> str:
    """Render a comprehensive markdown document for the backlog.

    Sections:
    1. Title and summary stats
    2. Summary tables (by status, by risk)
    3. Items grouped by milestone
    4. Risk breakdown section
    5. Dependency list section
    """
    summary = summarize_backlog(backlog)
    lines: List[str] = []

    # 1. Title and summary stats
    lines.append(f"# Backlog: {backlog.backlog_id}")
    lines.append("")
    lines.append(f"**Expected tasks:** {backlog.total_expected_tasks}")
    lines.append(f"**Actual items:** {len(backlog.items)}")
    lines.append(f"**Status:** {backlog.status}")
    if backlog.notes:
        lines.append("")
        lines.append("**Backlog notes:**")
        for note in backlog.notes:
            lines.append(f"- {note}")
    lines.append("")

    # 2. Summary tables
    lines.append("## Summary by Status")
    lines.append("")
    lines.append(_render_status_table(summary["status_counts"]))
    lines.append("")
    lines.append("## Summary by Risk Level")
    lines.append("")
    lines.append(_render_risk_table(summary["risk_counts"]))
    lines.append("")

    # 3. Items grouped by milestone
    milestone_groups: Dict[str, List[PrdBacklogItem]] = {}
    for item in backlog.items:
        milestone_groups.setdefault(item.milestone_id, []).append(item)

    lines.append("## Items by Milestone")
    lines.append("")
    for ms_id in sorted(milestone_groups):
        group = milestone_groups[ms_id]
        lines.append(f"## Milestone: {ms_id} ({len(group)} items)")
        lines.append("")
        for item in group:
            lines.append(_render_item_detail(item))

    # 4. Risk breakdown
    lines.append("## Risk Breakdown")
    lines.append("")
    risk_groups: Dict[str, List[PrdBacklogItem]] = {}
    for item in backlog.items:
        risk_groups.setdefault(item.risk_level, []).append(item)

    for risk in sorted(risk_groups):
        items_at_risk = risk_groups[risk]
        lines.append(f"### {risk} ({len(items_at_risk)} items)")
        lines.append("")
        for item in items_at_risk:
            lines.append(f"- `{item.task_id}` — {item.title} (milestone: {item.milestone_id})")
        lines.append("")

    # 5. Dependency list
    lines.append("## Dependencies")
    lines.append("")
    has_deps = False
    for item in sorted(backlog.items, key=lambda i: i.task_id):
        if item.dependencies:
            has_deps = True
            deps_str = ", ".join(item.dependencies)
            lines.append(f"- `{item.task_id}` depends on: {deps_str}")
    if not has_deps:
        lines.append("No dependencies.")
    lines.append("")

    return "\n".join(lines)


def render_backlog_summary_markdown(backlog: PrdBacklog) -> str:
    """Render a short summary markdown: stats + counts only."""
    summary = summarize_backlog(backlog)
    lines: List[str] = []

    lines.append(f"# Backlog Summary: {backlog.backlog_id}")
    lines.append("")
    lines.append(f"**Expected tasks:** {backlog.total_expected_tasks}")
    lines.append(f"**Actual items:** {len(backlog.items)}")
    lines.append(f"**Status:** {backlog.status}")
    lines.append("")

    lines.append("## Status Counts")
    lines.append("")
    lines.append(_render_status_table(summary["status_counts"]))
    lines.append("")

    lines.append("## Risk Counts")
    lines.append("")
    lines.append(_render_risk_table(summary["risk_counts"]))
    lines.append("")

    return "\n".join(lines)
