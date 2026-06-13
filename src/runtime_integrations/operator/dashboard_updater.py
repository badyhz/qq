"""Dashboard updater. Generates HTML dashboard from runtime system state."""
from __future__ import annotations

import json
import pathlib


def render_dashboard_html(state: dict) -> str:
    """Render HTML dashboard from runtime system state."""
    mode = state.get("current_mode", "UNKNOWN")
    submit = state.get("submit_permission", "UNKNOWN")
    healthy = state.get("system_healthy", False)
    dry_run = state.get("dry_run", True)
    stats = state.get("runtime_stats", {})
    blockers = state.get("critical_blockers", [])
    alert_sources = state.get("active_alert_sources", [])

    health_text = "HEALTHY" if healthy else "UNHEALTHY"
    health_color = "#27ae60" if healthy else "#e74c3c"
    mode_color = "#3498db"

    blocker_html = ""
    if blockers:
        items = "".join(f"<li>{b}</li>" for b in blockers)
        blocker_html = f'<div class="card warn"><h3>Critical Blockers</h3><ul>{items}</ul></div>'
    else:
        blocker_html = '<div class="card ok"><h3>Critical Blockers</h3><p>None</p></div>'

    alerts_html = "".join(f"<span class='tag'>{s}</span>" for s in alert_sources)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Operator Dashboard — Runtime</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f6fa; color: #2d3436; }}
.header {{ background: #2d3436; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
.header h1 {{ margin: 0; font-size: 24px; }}
.header .mode {{ display: inline-block; padding: 4px 12px; border-radius: 4px; background: {mode_color}; margin-top: 8px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px; }}
.card {{ background: white; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
.card h3 {{ margin: 0 0 8px 0; font-size: 13px; color: #636e72; text-transform: uppercase; }}
.card .value {{ font-size: 28px; font-weight: bold; }}
.card.ok {{ border-left: 4px solid #27ae60; }}
.card.warn {{ border-left: 4px solid #e74c3c; }}
.tag {{ display: inline-block; padding: 2px 8px; border-radius: 4px; background: #dfe6e9; margin: 2px; font-size: 12px; }}
.section {{ background: white; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; }}
.section h2 {{ margin: 0 0 12px 0; font-size: 16px; }}
.stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; }}
.stat {{ padding: 8px; background: #f8f9fa; border-radius: 4px; }}
.stat .label {{ font-size: 11px; color: #636e72; text-transform: uppercase; }}
.stat .num {{ font-size: 20px; font-weight: bold; }}
.footer {{ margin-top: 20px; text-align: center; color: #636e72; font-size: 12px; }}
.safety {{ background: #27ae60; color: white; padding: 12px; border-radius: 8px; margin-bottom: 20px; text-align: center; font-weight: bold; }}
</style>
</head>
<body>
<div class="header">
<h1>Operator Dashboard — Runtime</h1>
<div class="mode">{mode}</div>
</div>
<div class="safety">REAL TRADING: NOT ALLOWED | TESTNET SUBMIT: NOT ALLOWED | DRY-RUN: ENFORCED</div>
<div class="grid">
<div class="card"><h3>System Health</h3><div class="value" style="color:{health_color}">{health_text}</div></div>
<div class="card"><h3>Submit Permission</h3><div class="value">{submit}</div></div>
<div class="card"><h3>Dry Run</h3><div class="value">{"ON" if dry_run else "OFF"}</div></div>
<div class="card"><h3>High-Risk Isolated</h3><div class="value">{stats.get("high_risk_isolated", 0)}</div></div>
</div>
<div class="section">
<h2>Runtime Statistics</h2>
<div class="stat-grid">
<div class="stat"><div class="label">Research Items</div><div class="num">{stats.get("research_items", 0)}</div></div>
<div class="stat"><div class="label">Shadow Signals</div><div class="num">{stats.get("shadow_signals", 0)}</div></div>
<div class="stat"><div class="label">Shadow Tickers</div><div class="num">{stats.get("shadow_tickers", 0)}</div></div>
<div class="stat"><div class="label">Alert Events</div><div class="num">{stats.get("alert_events", 0)}</div></div>
<div class="stat"><div class="label">Feishu Payloads</div><div class="num">{stats.get("feishu_payloads", 0)}</div></div>
<div class="stat"><div class="label">Testnet Intents</div><div class="num">{stats.get("testnet_intents", 0)}</div></div>
<div class="stat"><div class="label">Testnet Lifecycle</div><div class="num">{stats.get("testnet_lifecycle_events", 0)}</div></div>
<div class="stat"><div class="label">No-Submit Evidence</div><div class="num">{stats.get("no_submit_evidence", 0)}</div></div>
</div>
</div>
<div class="section">
<h2>Active Alert Sources</h2>
{alerts_html if alerts_html else "<p>None</p>"}
</div>
{blocker_html}
<div class="section">
<h2>Next Recommended Phase</h2>
<p style="font-size:18px;font-weight:bold;color:#3498db">{state.get("next_recommended_phase", "UNKNOWN")}</p>
</div>
<div class="footer">State ID: {state.get("state_id", "unknown")} | Timestamp: {state.get("timestamp", "unknown")}</div>
</body>
</html>"""


def write_dashboard(state: dict, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_dashboard_html(state), encoding="utf-8")
