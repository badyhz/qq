"""T1608: Renderer for FrozenBacklogSnapshot."""
from __future__ import annotations

import json

from core.frozen_backlog_snapshot import FrozenBacklogSnapshot


def render_snapshot_md(snapshot: FrozenBacklogSnapshot) -> str:
    """Render snapshot as markdown. Pure function."""
    report_json = json.dumps(snapshot.report_data, indent=2, sort_keys=True, ensure_ascii=False)
    lines = [
        "# Frozen Backlog Snapshot",
        "",
        f"- **ID:** {snapshot.snapshot_id}",
        f"- **Version:** {snapshot.version}",
        f"- **Created:** {snapshot.created_at_iso}",
        "",
        "## Report Data",
        "",
        "```json",
        report_json,
        "```",
        "",
    ]
    return "\n".join(lines)
