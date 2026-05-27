"""Release hold dashboard renderer — pure markdown rendering functions.

T1398 — Pure functions, no I/O, no side effects.
"""

from core.release_hold_dashboard import ReleaseHoldDashboard


def render_release_hold_dashboard_md(dashboard: ReleaseHoldDashboard) -> str:
    """Render a ReleaseHoldDashboard to markdown."""
    lines = [
        f"# Release Hold Dashboard: {dashboard.dashboard_id}",
        "",
        f"**Hold Status:** {dashboard.hold_status}",
        f"**Frozen Files:** {dashboard.frozen_count}",
        f"**Medium-Risk Files:** {dashboard.medium_count}",
        "",
        "## Governance Layers",
    ]
    for layer in dashboard.governance_layers:
        lines.append(f"- {layer}")
    lines.extend([
        "",
        "## Next Human Action",
        dashboard.next_human_action,
    ])
    return "\n".join(lines)


def render_hold_status_md(dashboard: ReleaseHoldDashboard) -> str:
    """Render just the hold status line."""
    return f"**Hold Status:** {dashboard.hold_status}"
