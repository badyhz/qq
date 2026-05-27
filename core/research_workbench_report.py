"""Research workbench report renderers — markdown, JSON, HTML.

All renderers are pure, deterministic, no external assets.
No network, no exchange, no live.
"""
from __future__ import annotations

from typing import Any, Dict


def render_markdown_report(data: Dict[str, Any]) -> str:
    """Render workbench data as Markdown report."""
    lines = ["# Multi-Strategy Research Workbench Report", ""]

    # Executive summary
    lines.append("## Executive Summary")
    lines.append("")
    strategy_count = data.get("strategy_count", 0)
    total_rows = data.get("total_rows", 0)
    lines.append(f"- Strategies evaluated: {strategy_count}")
    lines.append(f"- Total matrix rows: {total_rows}")
    lines.append(f"- Release hold: HOLD")
    lines.append("")

    # Strategy registry
    registry = data.get("strategy_registry", {})
    if registry:
        lines.append("## Strategy Registry")
        lines.append("")
        lines.append(f"- Registered strategies: {registry.get('strategy_count', 0)}")
        lines.append(f"- Validation status: {registry.get('validation_status', 'N/A')}")
        lines.append("")

    # Parameter search
    search = data.get("parameter_search", {})
    if search:
        lines.append("## Parameter Search")
        lines.append("")
        lines.append(f"- Search budget: {search.get('search_budget', 0)}")
        lines.append(f"- Expanded combinations: {search.get('expanded_combinations', 0)}")
        lines.append(f"- Evaluated combinations: {search.get('evaluated_combinations', 0)}")
        lines.append(f"- Budget truncated: {search.get('budget_truncated', False)}")
        lines.append("")

    # Results summary
    results = data.get("results", {})
    if results:
        lines.append("## Results Summary")
        lines.append("")
        lines.append(f"- Total rows: {results.get('total_rows', 0)}")
        lines.append(f"- Evaluated: {results.get('evaluated_rows', 0)}")
        lines.append(f"- Skipped: {results.get('skipped_rows', 0)}")
        lines.append("")

    # Portfolio summary
    portfolio = data.get("portfolio_summary", {})
    if portfolio:
        lines.append("## Portfolio Aggregation")
        lines.append("")
        lines.append(f"- Total trades: {portfolio.get('total_trades', 0)}")
        lines.append(f"- Aggregate expectancy R: {portfolio.get('aggregate_expectancy_r', 0)}")
        lines.append(f"- Max drawdown approx: {portfolio.get('max_drawdown_approx', 0)}")
        lines.append("")
        lines.append("*Portfolio aggregation is offline research only and does not imply executable portfolio allocation.*")
        lines.append("")

    # Comparison
    comparison = data.get("comparison", {})
    if comparison:
        lines.append("## Strategy Comparison")
        lines.append("")
        for rank in comparison.get("strategy_rankings", []):
            lines.append(f"- {rank.get('strategy_id', 'N/A')}: score={rank.get('avg_score', 0):.4f}, trades={rank.get('total_trades', 0)}")
        lines.append("")

    # Promotion
    promotions = data.get("promotion_recommendations", [])
    if promotions:
        lines.append("## Promotion Recommendations")
        lines.append("")
        for rec in promotions:
            lines.append(f"- {rec.get('strategy_id', 'N/A')} ({rec.get('symbol', 'N/A')}): **{rec.get('status', 'N/A')}**")
        lines.append("")

    # Safety
    manifest = data.get("manifest", {})
    if manifest:
        lines.append("## Safety Manifest")
        lines.append("")
        lines.append(f"- Release hold: {manifest.get('release_hold', 'N/A')}")
        lines.append(f"- No live: {manifest.get('no_live', 'N/A')}")
        lines.append(f"- No submit: {manifest.get('no_submit', 'N/A')}")
        lines.append(f"- No exchange: {manifest.get('no_exchange', 'N/A')}")
        lines.append(f"- No network: {manifest.get('no_network', 'N/A')}")
        lines.append("")

    return "\n".join(lines)


def render_html_report(data: Dict[str, Any]) -> str:
    """Render workbench data as static HTML report.

    No external JS, CSS, fonts, or remote assets.
    """
    md = render_markdown_report(data)
    # Simple HTML wrapper with inline CSS
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Multi-Strategy Research Workbench Report</title>
<style>
body {{ font-family: monospace; margin: 2em; background: #fff; color: #333; }}
h1 {{ color: #222; border-bottom: 2px solid #333; }}
h2 {{ color: #444; margin-top: 1.5em; }}
pre {{ background: #f5f5f5; padding: 1em; overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 0.5em; text-align: left; }}
th {{ background: #f0f0f0; }}
</style>
</head>
<body>
<pre>{_escape_html(md)}</pre>
</body>
</html>"""
    return html


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
