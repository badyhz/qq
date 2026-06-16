"""HTML dashboard — local inline-CSS report, no CDN, no network."""
from __future__ import annotations

from typing import Optional, List

from core.paper_trading.runtime_orchestrator import RuntimeResult


def generate_dashboard_html(result: RuntimeResult) -> str:
    """Generate a self-contained HTML dashboard from RuntimeResult."""
    alerts_html = ""
    if result.alerts:
        items = "".join(
            f'<li class="alert-{a.level.value.lower()}">[{a.level.value}] {a.category}: {a.message}</li>'
            for a in result.alerts
        )
        alerts_html = f"<h2>Alerts</h2><ul>{items}</ul>"

    safety_items = "".join(f"<li>{f}</li>" for f in result.safety_flags)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Paper Trading Dashboard</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; color: #333; }}
  .container {{ max-width: 900px; margin: 0 auto; }}
  h1 {{ color: #1a1a2e; border-bottom: 3px solid #16213e; padding-bottom: 10px; }}
  h2 {{ color: #16213e; margin-top: 30px; }}
  .card {{ background: white; border-radius: 8px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
  .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; }}
  .metric {{ text-align: center; }}
  .metric .value {{ font-size: 2em; font-weight: bold; color: #1a1a2e; }}
  .metric .label {{ font-size: 0.85em; color: #666; margin-top: 4px; }}
  .rating {{ display: inline-block; padding: 8px 20px; border-radius: 6px; font-size: 1.5em; font-weight: bold; }}
  .rating-A {{ background: #d4edda; color: #155724; }}
  .rating-B {{ background: #cce5ff; color: #004085; }}
  .rating-C {{ background: #fff3cd; color: #856404; }}
  .rating-D {{ background: #f8d7da; color: #721c24; }}
  .rating-REJECT {{ background: #f5c6cb; color: #721c24; }}
  .alert-warning {{ color: #856404; }}
  .alert-critical {{ color: #721c24; font-weight: bold; }}
  .alert-info {{ color: #0c5460; }}
  .safety {{ background: #e8f5e9; border-left: 4px solid #4caf50; padding: 15px; margin-top: 20px; }}
  .safety ul {{ margin: 5px 0; padding-left: 20px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
  th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
  th {{ background: #16213e; color: white; }}
  .footer {{ margin-top: 30px; padding: 15px; background: #1a1a2e; color: #aaa; border-radius: 8px; text-align: center; font-size: 0.85em; }}
</style>
</head>
<body>
<div class="container">
<h1>Paper Trading Dashboard</h1>

<div class="card">
  <div style="text-align:center;">
    <span class="rating rating-{result.rating}">{result.rating}</span>
    <p style="margin-top:10px;color:#666;">Score: {result.score:.1f} | Strategy: {result.strategy_name}</p>
  </div>
</div>

<div class="card">
  <div class="metric-grid">
    <div class="metric"><div class="value">{result.total_trades}</div><div class="label">Trades</div></div>
    <div class="metric"><div class="value">{result.win_rate:.1%}</div><div class="label">Win Rate</div></div>
    <div class="metric"><div class="value">{result.total_pnl:+.2f}</div><div class="label">Total PnL</div></div>
    <div class="metric"><div class="value">{result.fixtures_run}</div><div class="label">Fixtures Run</div></div>
    <div class="metric"><div class="value">{result.total_signals}</div><div class="label">Signals</div></div>
    <div class="metric"><div class="value">{result.total_rejected}</div><div class="label">Rejected</div></div>
  </div>
</div>

<div class="card">
  <h2>Pipeline</h2>
  <table>
    <tr><th>Stage</th><th>Count</th></tr>
    <tr><td>Fixtures loaded</td><td>{result.fixtures_run}</td></tr>
    <tr><td>Fixtures failed</td><td>{result.fixtures_failed}</td></tr>
    <tr><td>Signals generated</td><td>{result.total_signals}</td></tr>
    <tr><td>Plans created</td><td>{result.total_plans}</td></tr>
    <tr><td>Plans rejected</td><td>{result.total_rejected}</td></tr>
    <tr><td>Trades executed</td><td>{result.total_trades}</td></tr>
  </table>
</div>

{alerts_html}

<div class="safety">
  <strong>Safety Flags</strong>
  <ul>{safety_items}</ul>
</div>

<div class="footer">
  Paper Trading Dashboard | Mode: paper-only | No real orders | No network calls | Generated locally
</div>
</div>
</body>
</html>"""


def write_dashboard(result: RuntimeResult, output_path: str) -> None:
    """Write dashboard HTML to file."""
    html = generate_dashboard_html(result)
    with open(output_path, "w") as f:
        f.write(html)
