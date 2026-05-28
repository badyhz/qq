"""Research comparison report — markdown and HTML rendering.

Program G: Markdown Report.
Program H: Standalone HTML Report.
Render comparison analytics into human-readable reports.

No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

from typing import Any, Dict, List


def render_comparison_markdown(
    scorecard: Dict[str, Any],
    metrics_json: Dict[str, Any],
    pairwise_json: Dict[str, Any],
    trend_json: Dict[str, Any],
    regression_json: Dict[str, Any],
    manifest_json: Dict[str, Any],
) -> str:
    """Render research comparison markdown report."""
    lines: List[str] = []

    # 1. Executive comparison verdict
    lines.append("# Research Comparison Report")
    lines.append("")
    lines.append("## 1. Executive Comparison Verdict")
    lines.append("")
    best = scorecard.get("best_composite_score", "N/A")
    best_val = scorecard.get("best_composite_score_value", 0)
    safest = scorecard.get("safest_bundle", "N/A")
    lines.append(f"- **Best composite score**: {best} ({best_val:.4f})")
    lines.append(f"- **Safest bundle**: {safest}")
    lines.append(f"- **Promotion blocked**: {scorecard.get('promotion_blocked', True)}")
    lines.append(f"- **Reason**: {scorecard.get('promotion_block_reason', 'N/A')}")
    lines.append("")

    # 2. Bundle list
    lines.append("## 2. Bundle List")
    lines.append("")
    for m in metrics_json.get("metrics", []):
        lines.append(f"- **{m['label']}**: verdict={m['verdict']}, score={m['composite_score']:.4f}")
    lines.append("")

    # 3. Safety boundary
    lines.append("## 3. Safety Boundary")
    lines.append("")
    lines.append("| Flag | Status |")
    lines.append("|------|--------|")
    for m in metrics_json.get("metrics", []):
        for flag in ("release_hold", "advisory_only", "human_review_required", "no_network", "no_live", "no_submit", "no_exchange"):
            val = m.get(flag, "N/A")
            status = "PASS" if val in ("HOLD", True) else "FAIL"
            lines.append(f"| {m['label']}.{flag} | {status} |")
    lines.append("")

    # 4. Metric table
    lines.append("## 4. Metric Table")
    lines.append("")
    _metrics_list = metrics_json.get("metrics", [])
    if _metrics_list:
        headers = ["Label", "Score", "Stability", "Fragility", "NC Margin", "Crowding", "Blockers", "Warnings"]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for m in _metrics_list:
            lines.append(
                f"| {m['label']} | {m['composite_score']:.4f} | {m['stability_score']:.4f} | "
                f"{m['parameter_fragility']:.4f} | {m['negative_control_margin']:.4f} | "
                f"{m['portfolio_crowding_score']:.4f} | {m['blocker_count']} | {m['warning_count']} |"
            )
    lines.append("")

    # 5. Pairwise differences
    lines.append("## 5. Pairwise Differences")
    lines.append("")
    for comp in pairwise_json.get("comparisons", []):
        lines.append(f"### {comp['left_label']} vs {comp['right_label']}")
        lines.append("")
        lines.append(f"- Classification: **{comp['overall_classification']}**")
        lines.append(f"- Score delta: {comp['composite_score_delta']:.4f}")
        lines.append(f"- Blocker change: {comp['blocker_change']}")
        lines.append(f"- Warning change: {comp['warning_change']}")
        if comp.get("safety_flag_changes"):
            lines.append(f"- Safety changes: {', '.join(comp['safety_flag_changes'])}")
        ac = comp.get("artifact_changes", {})
        if ac.get("changed"):
            lines.append(f"- Changed artifacts: {', '.join(ac['changed'])}")
        if ac.get("added"):
            lines.append(f"- Added artifacts: {', '.join(ac['added'])}")
        if ac.get("removed"):
            lines.append(f"- Removed artifacts: {', '.join(ac['removed'])}")
        lines.append("")

    # 6. Trend analysis
    lines.append("## 6. Trend Analysis")
    lines.append("")
    if trend_json.get("bundle_count", 0) > 0:
        lines.append(f"- Overall trend: **{trend_json.get('overall_trend', 'N/A')}**")
        lines.append(f"- Bundles: {', '.join(trend_json.get('labels', []))}")
        for d in trend_json.get("detections", []):
            lines.append(f"- Detection: {d}")
        lines.append("")
        for t in trend_json.get("metric_trends", []):
            lines.append(f"- {t['metric']}: {t['trend_type']} (slope={t['slope']:.6f})")
    else:
        lines.append("- Trend analysis requires 3+ bundles")
    lines.append("")

    # 7. Regression detector
    lines.append("## 7. Regression Detector")
    lines.append("")
    lines.append(f"- Has regressions: {regression_json.get('has_regressions', False)}")
    lines.append(f"- Regression count: {regression_json.get('regression_count', 0)}")
    for reg in regression_json.get("regressions", []):
        lines.append(f"- **[{reg['severity']}]** {reg['description']}")
    lines.append("")

    # 8. Artifact drift
    lines.append("## 8. Artifact Drift")
    lines.append("")
    for comp in pairwise_json.get("comparisons", []):
        ac = comp.get("artifact_changes", {})
        if ac.get("changed") or ac.get("added") or ac.get("removed"):
            lines.append(f"### {comp['left_label']} vs {comp['right_label']}")
            for a in ac.get("changed", []):
                lines.append(f"- Changed: {a}")
            for a in ac.get("added", []):
                lines.append(f"- Added: {a}")
            for a in ac.get("removed", []):
                lines.append(f"- Removed: {a}")
    lines.append("")

    # 9. Negative control margin comparison
    lines.append("## 9. Negative Control Margin Comparison")
    lines.append("")
    for m in _metrics_list:
        lines.append(f"- {m['label']}: {m['negative_control_margin']:.4f}")
    lines.append("")

    # 10. Bootstrap uncertainty comparison
    lines.append("## 10. Bootstrap Uncertainty Comparison")
    lines.append("")
    for m in _metrics_list:
        lines.append(f"- {m['label']}: CI width={m['bootstrap_ci_width']:.4f}, worst-case={m['bootstrap_worst_case']:.4f}")
    lines.append("")

    # 11. Regime risk comparison
    lines.append("## 11. Regime Risk Comparison")
    lines.append("")
    for m in _metrics_list:
        lines.append(f"- {m['label']}: concentration_warnings={m['regime_concentration_warning_count']}")
    lines.append("")

    # 12. Portfolio overlap comparison
    lines.append("## 12. Portfolio Overlap Comparison")
    lines.append("")
    for m in _metrics_list:
        lines.append(f"- {m['label']}: crowding={m['portfolio_crowding_score']:.4f}, overlap_risk={m['overlap_risk']:.4f}")
    lines.append("")

    # 13. Human review recommendations
    lines.append("## 13. Human Review Recommendations")
    lines.append("")
    lines.append("Priority order for human review:")
    for i, label in enumerate(scorecard.get("review_priority", []), 1):
        lines.append(f"{i}. {label}")
    lines.append("")

    # 14. Advisory-only statement
    lines.append("## 14. Advisory-Only / No Auto-Promotion Statement")
    lines.append("")
    lines.append("**This report is advisory only. No auto-promotion. release_hold remains HOLD.**")
    lines.append("")
    lines.append("Human review is required before any promotion decision.")
    lines.append("No live trading, testnet submission, exchange interaction, or runtime integration is performed.")
    lines.append("")

    return "\n".join(lines)


def render_comparison_html(
    scorecard: Dict[str, Any],
    metrics_json: Dict[str, Any],
    pairwise_json: Dict[str, Any],
    trend_json: Dict[str, Any],
    regression_json: Dict[str, Any],
    manifest_json: Dict[str, Any],
) -> str:
    """Render standalone offline HTML comparison report."""
    md_content = render_comparison_markdown(
        scorecard, metrics_json, pairwise_json,
        trend_json, regression_json, manifest_json,
    )

    # Convert markdown to simple HTML
    html_body = _md_to_html_body(md_content)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Research Comparison Report</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px; color: #1a1a1a; background: #fff; line-height: 1.6; }}
h1 {{ font-size: 1.8em; border-bottom: 2px solid #333; padding-bottom: 8px; }}
h2 {{ font-size: 1.4em; border-bottom: 1px solid #ccc; padding-bottom: 4px; margin-top: 2em; }}
h3 {{ font-size: 1.1em; margin-top: 1.5em; }}
table {{ border-collapse: collapse; margin: 1em 0; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 8px 12px; text-align: left; }}
th {{ background: #f5f5f5; font-weight: 600; }}
tr:nth-child(even) {{ background: #fafafa; }}
code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }}
pre {{ background: #f5f5f5; padding: 16px; border-radius: 4px; overflow-x: auto; }}
ul, ol {{ padding-left: 1.5em; }}
li {{ margin: 0.3em 0; }}
.footer {{ margin-top: 3em; padding-top: 1em; border-top: 2px solid #333; font-size: 0.85em; color: #666; }}
</style>
</head>
<body>
{html_body}
<div class="footer">
<p><strong>Advisory only. No auto-promotion. release_hold remains HOLD.</strong></p>
<p>Generated by research_comparison_analytics. Offline only. No network.</p>
</div>
</body>
</html>"""


def _md_to_html_body(md: str) -> str:
    """Simple markdown to HTML conversion for standalone report."""
    import re
    lines = md.split("\n")
    html_lines: List[str] = []
    in_table = False
    in_list = False
    table_header_done = False

    for line in lines:
        stripped = line.strip()

        # Headers
        if stripped.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            if in_table:
                html_lines.append("</table>")
                in_table = False
                table_header_done = False
            html_lines.append(f"<h3>{_md_inline(stripped[4:])}</h3>")
            continue
        if stripped.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            if in_table:
                html_lines.append("</table>")
                in_table = False
                table_header_done = False
            html_lines.append(f"<h2>{_md_inline(stripped[3:])}</h2>")
            continue
        if stripped.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            if in_table:
                html_lines.append("</table>")
                in_table = False
                table_header_done = False
            html_lines.append(f"<h1>{_md_inline(stripped[2:])}</h1>")
            continue

        # Table separator
        if re.match(r'^\|[\s\-|]+\|$', stripped):
            table_header_done = True
            continue

        # Table row
        if stripped.startswith("|") and stripped.endswith("|"):
            if not in_table:
                html_lines.append("<table>")
                in_table = True
                table_header_done = False
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            tag = "th" if not table_header_done else "td"
            row = "".join(f"<{tag}>{_md_inline(c)}</{tag}>" for c in cells)
            html_lines.append(f"<tr>{row}</tr>")
            continue

        # List item
        if stripped.startswith("- "):
            if in_table:
                html_lines.append("</table>")
                in_table = False
                table_header_done = False
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{_md_inline(stripped[2:])}</li>")
            continue

        # Numbered list
        m = re.match(r'^(\d+)\.\s+(.*)', stripped)
        if m:
            if in_table:
                html_lines.append("</table>")
                in_table = False
                table_header_done = False
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{m.group(1)}. {_md_inline(m.group(2))}</p>")
            continue

        # Close open elements
        if not stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            if in_table:
                html_lines.append("</table>")
                in_table = False
                table_header_done = False
            continue

        # Regular paragraph
        if in_table:
            html_lines.append("</table>")
            in_table = False
            table_header_done = False
        if in_list:
            html_lines.append("</ul>")
            in_list = False
        html_lines.append(f"<p>{_md_inline(stripped)}</p>")

    if in_list:
        html_lines.append("</ul>")
    if in_table:
        html_lines.append("</table>")

    return "\n".join(html_lines)


def _md_inline(text: str) -> str:
    """Convert inline markdown to HTML."""
    import re
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Code
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    return text
