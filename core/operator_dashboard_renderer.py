"""T39001 — Operator Dashboard Renderer.

Pure deterministic. No I/O. No network.
Generates HTML dashboard from operator console system status.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED_ODR = "HOLD"

STATUS_COLORS = {
    "TESTNET_DRY_RUN_PREP": "#3498db",
    "SHADOW_ONLY": "#95a5a6",
    "LIVE": "#e74c3c",
}

SUBMIT_COLORS = {
    "NO_SUBMIT": "#27ae60",
    "TESTNET_SUBMIT": "#f39c12",
    "LIVE_SUBMIT": "#e74c3c",
}

HEALTH_COLORS = {
    True: "#27ae60",
    False: "#e74c3c",
}


@dataclass(frozen=True)
class DashboardData:
    """Operator dashboard data snapshot."""
    snapshot_id: str
    current_mode: str
    submit_permission: str
    real_submit_allowed: bool
    testnet_submit_allowed: bool
    dry_run_allowed: bool
    frozen_cleanup_status: str
    promotion_status: str
    strategy_count: int
    active_alert_sources: tuple[str, ...]
    critical_blockers: tuple[str, ...]
    next_recommended_phase: str
    system_healthy: bool
    dry_run: bool

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "current_mode": self.current_mode,
            "submit_permission": self.submit_permission,
            "real_submit_allowed": self.real_submit_allowed,
            "testnet_submit_allowed": self.testnet_submit_allowed,
            "dry_run_allowed": self.dry_run_allowed,
            "frozen_cleanup_status": self.frozen_cleanup_status,
            "promotion_status": self.promotion_status,
            "strategy_count": self.strategy_count,
            "active_alert_sources": list(self.active_alert_sources),
            "critical_blockers": list(self.critical_blockers),
            "next_recommended_phase": self.next_recommended_phase,
            "system_healthy": self.system_healthy,
            "dry_run": self.dry_run,
        }


def build_dashboard_data(
    system_status: dict,
    snapshot_id: str = "default",
) -> DashboardData:
    """Build dashboard data from system status dict."""
    return DashboardData(
        snapshot_id=snapshot_id,
        current_mode=system_status.get("current_mode", "UNKNOWN"),
        submit_permission=system_status.get("submit_permission", "UNKNOWN"),
        real_submit_allowed=system_status.get("real_submit_allowed", False),
        testnet_submit_allowed=system_status.get("testnet_submit_allowed", False),
        dry_run_allowed=system_status.get("dry_run_allowed", True),
        frozen_cleanup_status=system_status.get("frozen_cleanup_status", "UNKNOWN"),
        promotion_status=system_status.get("promotion_status", "UNKNOWN"),
        strategy_count=system_status.get("strategy_count", 0),
        active_alert_sources=tuple(system_status.get("active_alert_sources", [])),
        critical_blockers=tuple(system_status.get("critical_blockers", [])),
        next_recommended_phase=system_status.get("next_recommended_phase", "UNKNOWN"),
        system_healthy=system_status.get("system_healthy", False),
        dry_run=system_status.get("dry_run", True),
    )


def compute_dashboard_hash(data: DashboardData) -> str:
    raw = json.dumps(data.to_dict(), sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_dashboard_html(data: DashboardData) -> str:
    """Render HTML dashboard from dashboard data."""
    mode_color = STATUS_COLORS.get(data.current_mode, "#95a5a6")
    submit_color = SUBMIT_COLORS.get(data.submit_permission, "#95a5a6")
    health_color = HEALTH_COLORS.get(data.system_healthy, "#95a5a6")
    health_text = "HEALTHY" if data.system_healthy else "UNHEALTHY"
    blockers_html = ""
    if data.critical_blockers:
        items = "".join(f"<li>{b}</li>" for b in data.critical_blockers)
        blockers_html = f'<div class="blockers"><h3>Critical Blockers</h3><ul>{items}</ul></div>'
    else:
        blockers_html = '<div class="blockers clear"><h3>Critical Blockers</h3><p>None</p></div>'

    alerts_html = "".join(f"<span class='tag'>{s}</span>" for s in data.active_alert_sources)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Operator Dashboard</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f6fa; color: #2d3436; }}
.header {{ background: #2d3436; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
.header h1 {{ margin: 0; font-size: 24px; }}
.header .mode {{ display: inline-block; padding: 4px 12px; border-radius: 4px; background: {mode_color}; margin-top: 8px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin-bottom: 20px; }}
.card {{ background: white; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
.card h3 {{ margin: 0 0 8px 0; font-size: 14px; color: #636e72; text-transform: uppercase; }}
.card .value {{ font-size: 28px; font-weight: bold; }}
.status-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
.status-item {{ display: flex; align-items: center; gap: 8px; }}
.dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
.dot.green {{ background: #27ae60; }}
.dot.red {{ background: #e74c3c; }}
.dot.yellow {{ background: #f39c12; }}
.dot.blue {{ background: #3498db; }}
.tag {{ display: inline-block; padding: 2px 8px; border-radius: 4px; background: #dfe6e9; margin: 2px; font-size: 12px; }}
.blockers {{ background: white; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; }}
.blockers.clear {{ border-left: 4px solid #27ae60; }}
.blockers h3 {{ margin: 0 0 8px 0; }}
.next-action {{ background: #2d3436; color: white; border-radius: 8px; padding: 16px; }}
.next-action h3 {{ margin: 0 0 8px 0; color: #dfe6e9; }}
.next-action .phase {{ font-size: 18px; font-weight: bold; color: #74b9ff; }}
.footer {{ margin-top: 20px; text-align: center; color: #636e72; font-size: 12px; }}
</style>
</head>
<body>
<div class="header">
<h1>Operator Dashboard</h1>
<div class="mode">{data.current_mode}</div>
</div>
<div class="grid">
<div class="card">
<h3>System Health</h3>
<div class="value" style="color: {health_color}">{health_text}</div>
</div>
<div class="card">
<h3>Submit Permission</h3>
<div class="value" style="color: {submit_color}">{data.submit_permission}</div>
</div>
<div class="card">
<h3>Strategies</h3>
<div class="value">{data.strategy_count}</div>
</div>
<div class="card">
<h3>Dry Run</h3>
<div class="value">{"ENABLED" if data.dry_run else "DISABLED"}</div>
</div>
</div>
<div class="grid">
<div class="card">
<h3>Status Flags</h3>
<div class="status-grid">
<div class="status-item"><span class="dot {"green" if data.dry_run_allowed else "red"}"></span> Dry Run Allowed</div>
<div class="status-item"><span class="dot {"green" if not data.real_submit_allowed else "red"}"></span> Real Submit Blocked</div>
<div class="status-item"><span class="dot {"green" if not data.testnet_submit_allowed else "yellow"}"></span> Testnet Submit Blocked</div>
<div class="status-item"><span class="dot blue"></span> Frozen Cleanup: {data.frozen_cleanup_status}</div>
<div class="status-item"><span class="dot blue"></span> Promotion: {data.promotion_status}</div>
</div>
</div>
<div class="card">
<h3>Active Alert Sources</h3>
{alerts_html if alerts_html else "<p>None</p>"}
</div>
</div>
{blockers_html}
<div class="next-action">
<h3>Next Recommended Phase</h3>
<div class="phase">{data.next_recommended_phase}</div>
</div>
<div class="footer">
Dashboard hash: {compute_dashboard_hash(data)[:16]}... | Snapshot: {data.snapshot_id}
</div>
</body>
</html>"""
    return html


def render_dashboard_markdown(data: DashboardData) -> str:
    """Render markdown summary of dashboard data."""
    lines = [
        "# Operator Dashboard Summary",
        "",
        f"- **Mode:** {data.current_mode}",
        f"- **Submit permission:** {data.submit_permission}",
        f"- **System health:** {'HEALTHY' if data.system_healthy else 'UNHEALTHY'}",
        f"- **Dry run:** {data.dry_run}",
        f"- **Strategy count:** {data.strategy_count}",
        f"- **Frozen cleanup:** {data.frozen_cleanup_status}",
        f"- **Promotion:** {data.promotion_status}",
        f"- **Next phase:** {data.next_recommended_phase}",
        "",
        "## Active Alert Sources",
        "",
    ]
    for s in data.active_alert_sources:
        lines.append(f"- {s}")
    lines.append("")
    lines.append("## Critical Blockers")
    lines.append("")
    if data.critical_blockers:
        for b in data.critical_blockers:
            lines.append(f"- {b}")
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def write_html(content: str, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def write_json(data: DashboardData, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data.to_dict(), indent=2), encoding="utf-8")


def write_manifest(data: DashboardData, out_path, release_hold: str) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "snapshot_id": data.snapshot_id,
        "current_mode": data.current_mode,
        "system_healthy": data.system_healthy,
        "dry_run": data.dry_run,
        "release_hold": release_hold,
        "dashboard_hash": compute_dashboard_hash(data),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(content: str, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
