"""Offline shadow report renderers -- pure functions, no I/O.

Consumes experiment result dicts and produces markdown, JSON, and HTML
report strings.  No file I/O, no network, no timestamps.
"""
from __future__ import annotations

import json
from typing import Any


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _fmt_r(value: float) -> str:
    return f"{value:+.3f}R"


def _fmt_float(value: float, decimals: int = 3) -> str:
    return f"{value:.{decimals}f}"


def _grade_color(grade: str) -> str:
    """Return hex color for a letter grade."""
    colors = {
        "A": "#22c55e",
        "B": "#84cc16",
        "C": "#eab308",
        "D": "#f97316",
        "F": "#ef4444",
        "P": "#22c55e",  # PASS
        "W": "#eab308",  # WATCH
        "R": "#ef4444",  # REJECT
    }
    letter = grade[0].upper() if grade else "F"
    return colors.get(letter, "#6b7280")


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------

def render_report_markdown(results: list[dict[str, Any]]) -> str:
    """Render experiment results as a markdown report.

    Parameters
    ----------
    results : list[dict]
        Each dict must have: experiment_id, symbol, timeframe, param_label,
        metrics (dict), and optionally scorecard (dict).

    Returns
    -------
    str
        Markdown-formatted report.
    """
    if not results:
        return "# Offline Shadow Research Report\n\nNo experiments to report.\n"

    lines: list[str] = []
    lines.append("# Offline Shadow Research Report")
    lines.append("")
    lines.append(f"**release_hold = HOLD** | Experiments: {len(results)}")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| ID | Symbol | TF | Params | Win Rate | Expectancy | PF | Grade |")
    lines.append("|---|--------|-----|--------|----------|------------|-----|-------|")

    for r in results:
        m = r.get("metrics", {})
        sc = r.get("scorecard", {})
        grade = sc.get("grade", "N/A")
        lines.append(
            f"| {r.get('experiment_id', '?')} "
            f"| {r.get('symbol', '?')} "
            f"| {r.get('timeframe', '?')} "
            f"| {r.get('param_label', '?')} "
            f"| {_fmt_pct(m.get('win_rate', 0.0))} "
            f"| {_fmt_r(m.get('expectancy_r', 0.0))} "
            f"| {_fmt_float(m.get('profit_factor', 0.0))} "
            f"| {grade} |"
        )

    lines.append("")

    # Per-experiment details
    lines.append("## Experiment Details")
    lines.append("")

    for r in results:
        m = r.get("metrics", {})
        sc = r.get("scorecard", {})
        lines.append(f"### {r.get('experiment_id', '?')}")
        lines.append("")
        lines.append(f"- **Symbol:** {r.get('symbol', '?')}")
        lines.append(f"- **Timeframe:** {r.get('timeframe', '?')}")
        lines.append(f"- **Parameters:** {r.get('param_label', '?')}")
        lines.append(f"- **Window:** {r.get('window_id', '?')}")
        lines.append("")
        lines.append("**Metrics**")
        lines.append("")
        lines.append(f"- Candidates: {m.get('candidate_count', 0)}")
        lines.append(f"- Win / Loss / Neutral: {m.get('win_count', 0)} / {m.get('loss_count', 0)} / {m.get('neutral_count', 0)}")
        lines.append(f"- Win Rate: {_fmt_pct(m.get('win_rate', 0.0))}")
        lines.append(f"- Avg Return: {_fmt_r(m.get('avg_return_r', 0.0))}")
        lines.append(f"- Expectancy: {_fmt_r(m.get('expectancy_r', 0.0))}")
        lines.append(f"- Max Drawdown: {_fmt_r(m.get('max_drawdown_r', 0.0))}")
        lines.append(f"- Profit Factor: {_fmt_float(m.get('profit_factor', 0.0))}")
        lines.append(f"- Sample Quality: {_fmt_float(m.get('sample_quality_score', 0.0))}")
        lines.append(f"- Coverage: {m.get('coverage_status', 'unknown')}")

        if sc:
            lines.append("")
            lines.append(f"**Scorecard: {sc.get('grade', 'N/A')}**")
            reason_codes = sc.get("reason_codes", [])
            if reason_codes:
                lines.append("")
                for rc in reason_codes:
                    lines.append(f"- {rc}")

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON renderer
# ---------------------------------------------------------------------------

def render_report_json(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Render experiment results as a structured JSON report.

    Parameters
    ----------
    results : list[dict]
        Same structure as render_report_markdown input.

    Returns
    -------
    dict
        Structured report with summary and experiments array.
    """
    if not results:
        return {
            "release_hold": "HOLD",
            "experiment_count": 0,
            "summary": {},
            "experiments": [],
        }

    # summary aggregation
    total_candidates = sum(
        r.get("metrics", {}).get("candidate_count", 0) for r in results
    )
    total_wins = sum(
        r.get("metrics", {}).get("win_count", 0) for r in results
    )
    total_losses = sum(
        r.get("metrics", {}).get("loss_count", 0) for r in results
    )
    avg_win_rate = (
        sum(r.get("metrics", {}).get("win_rate", 0.0) for r in results) / len(results)
    )
    avg_expectancy = (
        sum(r.get("metrics", {}).get("expectancy_r", 0.0) for r in results) / len(results)
    )
    avg_pf = (
        sum(r.get("metrics", {}).get("profit_factor", 0.0) for r in results) / len(results)
    )

    # best/worst by expectancy
    best = max(results, key=lambda r: r.get("metrics", {}).get("expectancy_r", 0.0))
    worst = min(results, key=lambda r: r.get("metrics", {}).get("expectancy_r", 0.0))

    summary = {
        "experiment_count": len(results),
        "total_candidates": total_candidates,
        "total_wins": total_wins,
        "total_losses": total_losses,
        "avg_win_rate": round(avg_win_rate, 6),
        "avg_expectancy_r": round(avg_expectancy, 6),
        "avg_profit_factor": round(avg_pf, 6),
        "best_experiment_id": best.get("experiment_id", ""),
        "worst_experiment_id": worst.get("experiment_id", ""),
    }

    experiments = []
    for r in results:
        experiments.append({
            "experiment_id": r.get("experiment_id", ""),
            "symbol": r.get("symbol", ""),
            "timeframe": r.get("timeframe", ""),
            "param_label": r.get("param_label", ""),
            "window_id": r.get("window_id", ""),
            "metrics": r.get("metrics", {}),
            "scorecard": r.get("scorecard", {}),
        })

    return {
        "release_hold": "HOLD",
        "experiment_count": len(results),
        "summary": summary,
        "experiments": experiments,
    }


# ---------------------------------------------------------------------------
# HTML renderer
# ---------------------------------------------------------------------------

def render_report_html(results: list[dict[str, Any]]) -> str:
    """Render experiment results as an HTML dashboard.

    Parameters
    ----------
    results : list[dict]
        Same structure as render_report_markdown input.

    Returns
    -------
    str
        Complete HTML document.
    """
    json_report = render_report_json(results)
    summary = json_report.get("summary", {})

    # Build experiment rows
    rows_html = ""
    for r in results:
        m = r.get("metrics", {})
        sc = r.get("scorecard", {})
        grade = sc.get("grade", "N/A")
        color = _grade_color(grade)
        rows_html += (
            "<tr>"
            f"<td>{_escape_html(r.get('experiment_id', ''))}</td>"
            f"<td>{_escape_html(r.get('symbol', ''))}</td>"
            f"<td>{_escape_html(r.get('timeframe', ''))}</td>"
            f"<td>{_escape_html(r.get('param_label', ''))}</td>"
            f"<td>{_fmt_pct(m.get('win_rate', 0.0))}</td>"
            f"<td>{_fmt_r(m.get('expectancy_r', 0.0))}</td>"
            f"<td>{_fmt_float(m.get('profit_factor', 0.0))}</td>"
            f"<td>{m.get('candidate_count', 0)}</td>"
            f"<td style='color:{color};font-weight:bold'>{_escape_html(grade)}</td>"
            "</tr>\n"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Offline Shadow Research Report</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f8f9fa; color: #212529; }}
  .hold-banner {{ background: #dc3545; color: white; text-align: center; padding: 12px; font-weight: bold; font-size: 16px; border-radius: 6px; margin-bottom: 20px; }}
  .cards {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }}
  .card {{ background: white; border-radius: 8px; padding: 16px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); min-width: 140px; }}
  .card .label {{ font-size: 12px; color: #6c757d; text-transform: uppercase; }}
  .card .value {{ font-size: 24px; font-weight: bold; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  th {{ background: #343a40; color: white; padding: 10px 12px; text-align: left; font-size: 13px; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #dee2e6; font-size: 14px; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f1f3f5; }}
  h1 {{ margin: 0 0 8px; }}
  h2 {{ margin: 24px 0 12px; color: #495057; }}
</style>
</head>
<body>
<div class="hold-banner">release_hold = HOLD -- No Live Trading</div>
<h1>Offline Shadow Research Report</h1>

<div class="cards">
  <div class="card"><div class="label">Experiments</div><div class="value">{summary.get('experiment_count', 0)}</div></div>
  <div class="card"><div class="label">Total Candidates</div><div class="value">{summary.get('total_candidates', 0)}</div></div>
  <div class="card"><div class="label">Avg Win Rate</div><div class="value">{_fmt_pct(summary.get('avg_win_rate', 0.0))}</div></div>
  <div class="card"><div class="label">Avg Expectancy</div><div class="value">{_fmt_r(summary.get('avg_expectancy_r', 0.0))}</div></div>
  <div class="card"><div class="label">Avg Profit Factor</div><div class="value">{_fmt_float(summary.get('avg_profit_factor', 0.0))}</div></div>
</div>

<h2>Experiment Results</h2>
<table>
<thead>
<tr>
  <th>ID</th><th>Symbol</th><th>TF</th><th>Params</th>
  <th>Win Rate</th><th>Expectancy</th><th>PF</th><th>Candidates</th><th>Grade</th>
</tr>
</thead>
<tbody>
{rows_html}</tbody>
</table>
</body>
</html>"""

    return html
