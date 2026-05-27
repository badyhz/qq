"""Offline backtest report renderers — pure functions.

Renders backtest results as Markdown, JSON, and HTML.
No I/O, no network. All rendering is string-based.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Sequence


def _indent(text: str, level: int = 1) -> str:
    prefix = "  " * level
    return "\n".join(prefix + line for line in text.split("\n"))


def _section(title: str, level: int = 2) -> str:
    return f"{'#' * level} {title}\n"


def _table_row(cells: Sequence[str]) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _table_header(cols: Sequence[str]) -> str:
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    return _table_row(cols) + "\n" + sep


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def render_backtest_report_markdown(data: Dict[str, Any]) -> str:
    """Render backtest report as Markdown string.

    Expected data keys (all optional with defaults):
        title, release_hold, executive_summary, data_quality,
        walk_forward_matrix, top_params, rejected_params,
        robustness_table, symbol_breakdown, next_recommendation
    """
    sections: list[str] = []
    title = data.get("title", "Offline Backtest Report")
    sections.append(f"# {title}\n")

    # Safety boundary
    hold = data.get("release_hold", "HOLD")
    sections.append(_section("Safety Boundary"))
    sections.append(f"**Release Status:** `{hold}`\n")
    sections.append("This report is for offline research only. No live orders.\n")

    # Executive summary
    exec_sum = data.get("executive_summary", "")
    if exec_sum:
        sections.append(_section("Executive Summary"))
        sections.append(f"{exec_sum}\n")

    # Data quality
    dq = data.get("data_quality", {})
    if dq:
        sections.append(_section("Data Quality Summary"))
        sections.append(_table_header(["Symbol", "Timeframe", "Rows", "Clean", "Issues"]))
        for item in dq.get("items", []):
            sections.append(_table_row([
                str(item.get("symbol", "")),
                str(item.get("timeframe", "")),
                str(item.get("total_rows", 0)),
                "Yes" if item.get("is_clean", False) else "No",
                str(item.get("issue_count", 0)),
            ]))
        sections.append("")

    # Walk-forward matrix
    wf = data.get("walk_forward_matrix", [])
    if wf:
        sections.append(_section("Walk-Forward Matrix"))
        cols = ["Split", "Symbol", "Trades", "Expectancy", "Win Rate", "Max DD", "Grade"]
        sections.append(_table_header(cols))
        for row in wf:
            sections.append(_table_row([
                str(row.get("split_id", "")),
                str(row.get("symbol", "")),
                str(row.get("trade_count", 0)),
                f"{row.get('expectancy_r', 0):.3f}",
                f"{row.get('win_rate', 0):.1%}",
                f"{row.get('max_drawdown_r', 0):.2f}",
                str(row.get("grade", "")),
            ]))
        sections.append("")

    # Top parameter sets
    top = data.get("top_params", [])
    if top:
        sections.append(_section("Top Parameter Sets"))
        cols = ["Rank", "Param ID", "Quality Score", "Expectancy", "PF", "Trades", "Grade"]
        sections.append(_table_header(cols))
        for i, p in enumerate(top, 1):
            sections.append(_table_row([
                str(i),
                str(p.get("param_id", "")),
                f"{p.get('quality_adjusted_score', 0):.3f}",
                f"{p.get('expectancy_r', 0):.3f}",
                f"{p.get('profit_factor', 0):.2f}",
                str(p.get("trade_count", 0)),
                str(p.get("grade", "")),
            ]))
        sections.append("")

    # Rejected parameter sets
    rej = data.get("rejected_params", [])
    if rej:
        sections.append(_section("Rejected Parameter Sets"))
        for p in rej:
            reasons = ", ".join(p.get("reasons", []))
            sections.append(f"- **{p.get('param_id', 'unknown')}**: {reasons}")
        sections.append("")

    # Robustness table
    rob = data.get("robustness_table", [])
    if rob:
        sections.append(_section("Robustness Analysis"))
        cols = ["Check", "Robust", "Passes", "Fails", "Detail"]
        sections.append(_table_header(cols))
        for r in rob:
            sections.append(_table_row([
                str(r.get("check_name", "")),
                "Yes" if r.get("is_robust", False) else "No",
                str(len(r.get("passes", []))),
                str(len(r.get("fails", []))),
                str(r.get("detail", "")),
            ]))
        sections.append("")

    # Symbol/timeframe breakdown
    sb = data.get("symbol_breakdown", [])
    if sb:
        sections.append(_section("Symbol/Timeframe Breakdown"))
        cols = ["Symbol", "Timeframe", "Runs", "Avg Expectancy", "Best Grade"]
        sections.append(_table_header(cols))
        for s in sb:
            sections.append(_table_row([
                str(s.get("symbol", "")),
                str(s.get("timeframe", "")),
                str(s.get("run_count", 0)),
                f"{s.get('avg_expectancy', 0):.3f}",
                str(s.get("best_grade", "")),
            ]))
        sections.append("")

    # Next recommendation
    rec = data.get("next_recommendation", "")
    if rec:
        sections.append(_section("Next Research Recommendation"))
        sections.append(f"{rec}\n")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

def render_backtest_report_json(data: Dict[str, Any]) -> str:
    """Render backtest report as JSON string."""
    return json.dumps(data, indent=2, default=str)


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def render_backtest_report_html(data: Dict[str, Any]) -> str:
    """Render backtest report as HTML string.

    Same data structure as markdown renderer.
    """
    title = data.get("title", "Offline Backtest Report")
    hold = data.get("release_hold", "HOLD")
    exec_sum = data.get("executive_summary", "")

    parts: list[str] = [
        "<!DOCTYPE html>",
        "<html><head>",
        f"<title>{title}</title>",
        "<style>",
        "body { font-family: sans-serif; max-width: 960px; margin: 0 auto; padding: 20px; }",
        "table { border-collapse: collapse; width: 100%; margin: 10px 0; }",
        "th, td { border: 1px solid #ddd; padding: 6px 10px; text-align: left; }",
        "th { background: #f5f5f5; }",
        ".hold { background: #fff3cd; padding: 10px; border: 1px solid #ffc107; margin: 10px 0; }",
        ".pass { color: green; } .reject { color: red; } .watch { color: orange; }",
        "</style>",
        "</head><body>",
        f"<h1>{title}</h1>",
    ]

    # Safety boundary
    parts.append(f'<div class="hold"><strong>Safety Boundary:</strong> {hold} — '
                 'This report is for offline research only. No live orders.</div>')

    # Executive summary
    if exec_sum:
        parts.append(f"<h2>Executive Summary</h2><p>{exec_sum}</p>")

    # Data quality
    dq = data.get("data_quality", {})
    if dq:
        parts.append("<h2>Data Quality Summary</h2>")
        parts.append("<table><tr><th>Symbol</th><th>Timeframe</th>"
                     "<th>Rows</th><th>Clean</th><th>Issues</th></tr>")
        for item in dq.get("items", []):
            clean = "Yes" if item.get("is_clean", False) else "No"
            parts.append(f"<tr><td>{item.get('symbol', '')}</td>"
                         f"<td>{item.get('timeframe', '')}</td>"
                         f"<td>{item.get('total_rows', 0)}</td>"
                         f"<td>{clean}</td>"
                         f"<td>{item.get('issue_count', 0)}</td></tr>")
        parts.append("</table>")

    # Walk-forward matrix
    wf = data.get("walk_forward_matrix", [])
    if wf:
        parts.append("<h2>Walk-Forward Matrix</h2>")
        parts.append("<table><tr><th>Split</th><th>Symbol</th><th>Trades</th>"
                     "<th>Expectancy</th><th>Win Rate</th><th>Max DD</th><th>Grade</th></tr>")
        for row in wf:
            grade = row.get("grade", "")
            css = "pass" if grade == "PASS" else ("reject" if grade == "REJECT" else "watch")
            parts.append(
                f'<tr><td>{row.get("split_id", "")}</td>'
                f'<td>{row.get("symbol", "")}</td>'
                f'<td>{row.get("trade_count", 0)}</td>'
                f'<td>{row.get("expectancy_r", 0):.3f}</td>'
                f'<td>{row.get("win_rate", 0):.1%}</td>'
                f'<td>{row.get("max_drawdown_r", 0):.2f}</td>'
                f'<td class="{css}">{grade}</td></tr>'
            )
        parts.append("</table>")

    # Top params
    top = data.get("top_params", [])
    if top:
        parts.append("<h2>Top Parameter Sets</h2>")
        parts.append("<table><tr><th>Rank</th><th>Param ID</th><th>Quality Score</th>"
                     "<th>Expectancy</th><th>PF</th><th>Trades</th><th>Grade</th></tr>")
        for i, p in enumerate(top, 1):
            parts.append(
                f'<tr><td>{i}</td><td>{p.get("param_id", "")}</td>'
                f'<td>{p.get("quality_adjusted_score", 0):.3f}</td>'
                f'<td>{p.get("expectancy_r", 0):.3f}</td>'
                f'<td>{p.get("profit_factor", 0):.2f}</td>'
                f'<td>{p.get("trade_count", 0)}</td>'
                f'<td>{p.get("grade", "")}</td></tr>'
            )
        parts.append("</table>")

    # Rejected
    rej = data.get("rejected_params", [])
    if rej:
        parts.append("<h2>Rejected Parameter Sets</h2><ul>")
        for p in rej:
            reasons = ", ".join(p.get("reasons", []))
            parts.append(f'<li><strong>{p.get("param_id", "unknown")}</strong>: {reasons}</li>')
        parts.append("</ul>")

    # Robustness
    rob = data.get("robustness_table", [])
    if rob:
        parts.append("<h2>Robustness Analysis</h2>")
        parts.append("<table><tr><th>Check</th><th>Robust</th><th>Passes</th>"
                     "<th>Fails</th><th>Detail</th></tr>")
        for r in rob:
            robust = "Yes" if r.get("is_robust", False) else "No"
            parts.append(
                f'<tr><td>{r.get("check_name", "")}</td><td>{robust}</td>'
                f'<td>{len(r.get("passes", []))}</td>'
                f'<td>{len(r.get("fails", []))}</td>'
                f'<td>{r.get("detail", "")}</td></tr>'
            )
        parts.append("</table>")

    # Symbol breakdown
    sb = data.get("symbol_breakdown", [])
    if sb:
        parts.append("<h2>Symbol/Timeframe Breakdown</h2>")
        parts.append("<table><tr><th>Symbol</th><th>Timeframe</th><th>Runs</th>"
                     "<th>Avg Expectancy</th><th>Best Grade</th></tr>")
        for s in sb:
            parts.append(
                f'<tr><td>{s.get("symbol", "")}</td>'
                f'<td>{s.get("timeframe", "")}</td>'
                f'<td>{s.get("run_count", 0)}</td>'
                f'<td>{s.get("avg_expectancy", 0):.3f}</td>'
                f'<td>{s.get("best_grade", "")}</td></tr>'
            )
        parts.append("</table>")

    # Next recommendation
    rec = data.get("next_recommendation", "")
    if rec:
        parts.append(f"<h2>Next Research Recommendation</h2><p>{rec}</p>")

    parts.append("</body></html>")
    return "\n".join(parts)
