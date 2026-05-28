"""Research static report renderer — HTML and Markdown.

Programs D and E. Offline only. No CDN. No external JS. No network.
"""
from __future__ import annotations

import html
import json
from typing import Any, Dict, List

ADVISORY_DISCLAIMER = (
    "ADVISORY ONLY — This research output is for analysis purposes only. "
    "It does not constitute trading advice and must not be used for live trading, "
    "testnet submission, or any form of automated order placement."
)

CHECKLIST_ITEMS = (
    "Review safety flags (all must pass)",
    "Review blockers (hard blocks must be empty for PASS)",
    "Review negative controls (must beat random/shuffled/inverted)",
    "Review bootstrap confidence intervals (CI must not include zero)",
    "Review regime concentration (no single regime > 80% weight)",
    "Review portfolio overlap risk (overlap must be below threshold)",
    "Review reproducibility (input/output hashes must match on rerun)",
    "Confirm release_hold remains HOLD",
    "Confirm no runtime/testnet/live promotion",
)


def render_html_report(
    review_model: Dict[str, Any],
    browser_index: Dict[str, Any],
    schema_validation: Dict[str, Any],
    generated_at: str = "deterministic",
) -> str:
    """Render standalone offline HTML report. No CDN. Inline CSS only."""
    e = html.escape
    parts = [
        "<!DOCTYPE html>",
        "<html lang='en'><head>",
        "<meta charset='utf-8'>",
        f"<title>{e('Artifact Browser Report')}</title>",
        "<style>",
        "body{font-family:system-ui,-apple-system,sans-serif;margin:0;padding:2em;"
        "max-width:960px;background:#fff;color:#222;line-height:1.5}",
        "h1{font-size:1.5em;border-bottom:2px solid #333;padding-bottom:0.3em}",
        "h2{font-size:1.2em;margin-top:1.5em;color:#444}",
        "h3{font-size:1.05em;margin-top:1em}",
        "table{border-collapse:collapse;width:100%;margin:0.5em 0}",
        "th,td{border:1px solid #ddd;padding:6px 10px;text-align:left}",
        "th{background:#f5f5f5;font-weight:600}",
        ".pass{color:#0a0;font-weight:bold}",
        ".fail{color:#c00;font-weight:bold}",
        ".partial{color:#c60;font-weight:bold}",
        ".warn{color:#c00}",
        ".ok{color:#0a0}",
        ".hold{background:#ff0;padding:2px 8px;font-weight:bold;display:inline-block}",
        ".section{margin:1em 0;padding:1em;border:1px solid #eee;border-radius:4px}",
        ".disclaimer{background:#fff3cd;border:1px solid #ffc107;padding:1em;"
        "margin:1em 0;font-weight:bold}",
        "ul{padding-left:1.5em}",
        "li{margin:0.2em 0}",
        ".checklist li{margin:0.3em 0}",
        "</style>",
        "</head><body>",
    ]

    # Section 1: Executive verdict
    verdict = review_model.get("verdict", "UNKNOWN")
    score = review_model.get("composite_score", 0)
    completeness = review_model.get("evidence_completeness", 0)
    vclass = "pass" if verdict == "PASS" else ("partial" if verdict == "PARTIAL" else "fail")

    parts.extend([
        f"<h1>Artifact Browser Report</h1>",
        f"<p><em>Generated: {e(generated_at)}</em></p>",
        f"<div class='disclaimer'>{e(ADVISORY_DISCLAIMER)}</div>",
        "<div class='section'>",
        f"<h2>1. Executive Verdict</h2>",
        f"<p>Verdict: <span class='{vclass}'>{e(verdict)}</span></p>",
        f"<p>Composite Score: <strong>{score:.4f}</strong></p>",
        f"<p>Evidence Completeness: <strong>{completeness:.4f}</strong></p>",
        "</div>",
    ])

    # Section 2: Safety boundary
    sf = review_model.get("safety_flags", {})
    parts.extend([
        "<div class='section'>",
        "<h2>2. Safety Boundary</h2>",
        "<table>",
        "<tr><th>Flag</th><th>Status</th></tr>",
    ])
    for k in sorted(sf.keys()):
        v = sf[k]
        cls = "ok" if v else "fail"
        parts.append(f"<tr><td>{e(k)}</td><td class='{cls}'>{e(str(v))}</td></tr>")
    parts.extend(["</table>", "</div>"])

    # Section 3: Artifact coverage
    idx = browser_index
    parts.extend([
        "<div class='section'>",
        "<h2>3. Artifact Coverage</h2>",
        f"<p>Required present: {idx.get('required_present', 0)}</p>",
        f"<p>Required missing: <span class='{'ok' if idx.get('required_missing', 0) == 0 else 'fail'}'>"
        f"{idx.get('required_missing', 0)}</span></p>",
        f"<p>Optional present: {idx.get('optional_present', 0)}</p>",
        f"<p>Coverage: {review_model.get('required_artifact_coverage', 0):.1%}</p>",
        "</div>",
    ])

    # Section 4: Quality scorecard
    parts.extend([
        "<div class='section'>",
        "<h2>4. Quality Scorecard</h2>",
        "<table>",
        "<tr><th>Metric</th><th>Value</th></tr>",
        f"<tr><td>Composite Score</td><td>{score:.4f}</td></tr>",
        f"<tr><td>Evidence Completeness</td><td>{completeness:.4f}</td></tr>",
        f"<tr><td>Schema Validation</td><td class='{'pass' if schema_validation.get('status') == 'PASS' else 'fail'}'>"
        f"{e(schema_validation.get('status', 'UNKNOWN'))}</td></tr>",
        "</table>",
        "</div>",
    ])

    # Section 5: Blockers / warnings
    blockers = review_model.get("blockers", [])
    warnings = review_model.get("warnings", [])
    parts.extend([
        "<div class='section'>",
        "<h2>5. Blockers and Warnings</h2>",
    ])
    if blockers:
        parts.append("<h3>Blockers</h3><ul>")
        for b in blockers:
            parts.append(f"<li class='fail'>{e(str(b))}</li>")
        parts.append("</ul>")
    else:
        parts.append("<p class='ok'>No blockers</p>")
    if warnings:
        parts.append("<h3>Warnings</h3><ul>")
        for w in warnings:
            parts.append(f"<li class='warn'>{e(str(w))}</li>")
        parts.append("</ul>")
    else:
        parts.append("<p class='ok'>No warnings</p>")
    parts.append("</div>")

    # Section 6: Robustness labs
    strat = review_model.get("strategy_robustness_summary", {})
    parts.extend([
        "<div class='section'>",
        "<h2>6. Robustness Labs</h2>",
        f"<p>Strategy Robustness Verdict: <strong>{e(strat.get('verdict', 'UNKNOWN'))}</strong></p>",
    ])
    strategies = strat.get("strategies", {})
    if isinstance(strategies, dict) and strategies:
        parts.append("<table><tr><th>Strategy</th><th>Score</th></tr>")
        for k in sorted(strategies.keys()):
            v = strategies[k]
            if isinstance(v, dict):
                parts.append(f"<tr><td>{e(k)}</td><td>{e(str(v.get('score', 'N/A')))}</td></tr>")
            else:
                parts.append(f"<tr><td>{e(k)}</td><td>{e(str(v))}</td></tr>")
        parts.append("</table>")
    elif isinstance(strategies, list) and strategies:
        parts.append(f"<p>Strategies evaluated: {len(strategies)}</p>")
    parts.append("</div>")

    # Section 7: Negative controls
    nc = review_model.get("negative_control_summary", {})
    parts.extend([
        "<div class='section'>",
        "<h2>7. Negative Controls</h2>",
        f"<p>Verdict: <strong>{e(nc.get('verdict', 'UNKNOWN'))}</strong></p>",
    ])
    baselines = nc.get("baselines", {})
    if isinstance(baselines, dict) and baselines:
        parts.append("<table><tr><th>Baseline</th><th>Score</th></tr>")
        for k in sorted(baselines.keys()):
            v = baselines[k]
            if isinstance(v, dict):
                parts.append(f"<tr><td>{e(k)}</td><td>{e(str(v.get('score', 'N/A')))}</td></tr>")
            else:
                parts.append(f"<tr><td>{e(k)}</td><td>{e(str(v))}</td></tr>")
        parts.append("</table>")
    parts.append("</div>")

    # Section 8: Bootstrap confidence
    boot = review_model.get("bootstrap_confidence_summary", {})
    parts.extend([
        "<div class='section'>",
        "<h2>8. Bootstrap Confidence</h2>",
        f"<p>Verdict: <strong>{e(boot.get('verdict', 'UNKNOWN'))}</strong></p>",
        f"<p>CI Lower: {boot.get('ci_lower', 'N/A')}</p>",
        f"<p>CI Upper: {boot.get('ci_upper', 'N/A')}</p>",
        "</div>",
    ])

    # Section 9: Regime segmentation
    parts.extend([
        "<div class='section'>",
        "<h2>9. Regime Segmentation</h2>",
    ])
    rw = review_model.get("regime_warnings", [])
    if rw:
        parts.append("<ul>")
        for w in rw:
            parts.append(f"<li class='warn'>{e(str(w))}</li>")
        parts.append("</ul>")
    else:
        parts.append("<p class='ok'>No regime warnings</p>")
    parts.append("</div>")

    # Section 10: Portfolio risk
    overlap = review_model.get("portfolio_overlap_risk", {})
    parts.extend([
        "<div class='section'>",
        "<h2>10. Portfolio Risk</h2>",
        f"<p>Overlap Verdict: <strong>{e(overlap.get('verdict', 'UNKNOWN'))}</strong></p>",
    ])
    pairs = overlap.get("pairs", [])
    if pairs:
        parts.append(f"<p>Overlap pairs: {len(pairs)}</p>")
    parts.append("</div>")

    # Section 11: Reproducibility
    parts.extend([
        "<div class='section'>",
        "<h2>11. Reproducibility</h2>",
        f"<p>Status: <strong>{e(review_model.get('reproducibility_status', 'UNKNOWN'))}</strong></p>",
        "</div>",
    ])

    # Section 12: Human review checklist
    parts.extend([
        "<div class='section'>",
        "<h2>12. Human Review Checklist</h2>",
        "<ul class='checklist'>",
    ])
    for item in CHECKLIST_ITEMS:
        parts.append(f"<li>[ ] {e(item)}</li>")
    parts.extend(["</ul>", "</div>"])

    # Footer
    hold = sf.get("release_hold_is_HOLD", True)
    parts.extend([
        "<hr>",
        f"<p><small>release_hold: <span class='hold'>{'HOLD' if hold else 'NOT HOLD'}</span> | "
        "Advisory only. No auto-promotion.</small></p>",
        "</body></html>",
    ])

    return "\n".join(parts)


def render_markdown_report(
    review_model: Dict[str, Any],
    browser_index: Dict[str, Any],
    schema_validation: Dict[str, Any],
    generated_at: str = "deterministic",
) -> str:
    """Render artifact browser markdown report."""
    lines = [
        "# Artifact Browser Report",
        "",
        f"Generated: {generated_at}",
        "",
        ADVISORY_DISCLAIMER,
        "",
    ]

    # 1. Executive verdict
    verdict = review_model.get("verdict", "UNKNOWN")
    score = review_model.get("composite_score", 0)
    completeness = review_model.get("evidence_completeness", 0)
    lines.extend([
        "## 1. Executive Verdict",
        "",
        f"- Verdict: **{verdict}**",
        f"- Composite Score: {score:.4f}",
        f"- Evidence Completeness: {completeness:.4f}",
        "",
    ])

    # 2. Safety boundary
    sf = review_model.get("safety_flags", {})
    lines.extend(["## 2. Safety Boundary", ""])
    for k in sorted(sf.keys()):
        v = sf[k]
        mark = "PASS" if v else "FAIL"
        lines.append(f"- {k}: **{mark}**")
    lines.append("")

    # 3. Artifact coverage
    idx = browser_index
    lines.extend([
        "## 3. Artifact Coverage",
        "",
        f"- Required present: {idx.get('required_present', 0)}",
        f"- Required missing: {idx.get('required_missing', 0)}",
        f"- Optional present: {idx.get('optional_present', 0)}",
        f"- Coverage: {review_model.get('required_artifact_coverage', 0):.1%}",
        "",
    ])

    # 4. Quality scorecard
    lines.extend([
        "## 4. Quality Scorecard",
        "",
        f"- Composite Score: {score:.4f}",
        f"- Evidence Completeness: {completeness:.4f}",
        f"- Schema Validation: {schema_validation.get('status', 'UNKNOWN')}",
        "",
    ])

    # 5. Blockers / warnings
    blockers = review_model.get("blockers", [])
    warnings = review_model.get("warnings", [])
    lines.extend(["## 5. Blockers and Warnings", ""])
    if blockers:
        lines.append("### Blockers")
        for b in blockers:
            lines.append(f"- **{b}**")
        lines.append("")
    else:
        lines.append("No blockers.")
        lines.append("")
    if warnings:
        lines.append("### Warnings")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")
    else:
        lines.append("No warnings.")
        lines.append("")

    # 6. Robustness labs
    strat = review_model.get("strategy_robustness_summary", {})
    lines.extend([
        "## 6. Robustness Labs",
        "",
        f"- Strategy Robustness Verdict: **{strat.get('verdict', 'UNKNOWN')}**",
        "",
    ])
    strategies = strat.get("strategies", {})
    if isinstance(strategies, dict) and strategies:
        for k in sorted(strategies.keys()):
            v = strategies[k]
            if isinstance(v, dict):
                lines.append(f"  - {k}: {v.get('score', 'N/A')}")
            else:
                lines.append(f"  - {k}: {v}")
        lines.append("")
    elif isinstance(strategies, list) and strategies:
        lines.append(f"  - Strategies evaluated: {len(strategies)}")
        lines.append("")

    # 7. Negative controls
    nc = review_model.get("negative_control_summary", {})
    lines.extend([
        "## 7. Negative Controls",
        "",
        f"- Verdict: **{nc.get('verdict', 'UNKNOWN')}**",
        "",
    ])
    baselines = nc.get("baselines", {})
    if isinstance(baselines, dict) and baselines:
        for k in sorted(baselines.keys()):
            v = baselines[k]
            if isinstance(v, dict):
                lines.append(f"  - {k}: {v.get('score', 'N/A')}")
            else:
                lines.append(f"  - {k}: {v}")
        lines.append("")

    # 8. Bootstrap confidence
    boot = review_model.get("bootstrap_confidence_summary", {})
    lines.extend([
        "## 8. Bootstrap Confidence",
        "",
        f"- Verdict: **{boot.get('verdict', 'UNKNOWN')}**",
        f"- CI Lower: {boot.get('ci_lower', 'N/A')}",
        f"- CI Upper: {boot.get('ci_upper', 'N/A')}",
        "",
    ])

    # 9. Regime segmentation
    lines.extend(["## 9. Regime Segmentation", ""])
    rw = review_model.get("regime_warnings", [])
    if rw:
        for w in rw:
            lines.append(f"- {w}")
    else:
        lines.append("No regime warnings.")
    lines.append("")

    # 10. Portfolio risk
    overlap = review_model.get("portfolio_overlap_risk", {})
    lines.extend([
        "## 10. Portfolio Risk",
        "",
        f"- Overlap Verdict: **{overlap.get('verdict', 'UNKNOWN')}**",
    ])
    pairs = overlap.get("pairs", [])
    if pairs:
        lines.append(f"- Overlap pairs: {len(pairs)}")
    lines.append("")

    # 11. Reproducibility
    lines.extend([
        "## 11. Reproducibility",
        "",
        f"- Status: **{review_model.get('reproducibility_status', 'UNKNOWN')}**",
        "",
    ])

    # 12. Human review checklist
    lines.extend(["## 12. Human Review Checklist", ""])
    for item in CHECKLIST_ITEMS:
        lines.append(f"- [ ] {item}")
    lines.append("")

    # Footer
    hold = sf.get("release_hold_is_HOLD", True)
    lines.extend([
        "---",
        "",
        f"release_hold: **{'HOLD' if hold else 'NOT HOLD'}**",
        "",
        "**Advisory only. No auto-promotion. Human review required.**",
        "",
    ])

    return "\n".join(lines)


def render_human_review_checklist(
    review_model: Dict[str, Any],
    generated_at: str = "deterministic",
) -> Dict[str, Any]:
    """Generate human review checklist as JSON."""
    items = []
    for i, item in enumerate(CHECKLIST_ITEMS, 1):
        items.append({
            "id": i,
            "item": item,
            "checked": False,
            "notes": "",
        })

    return {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
        "verdict": review_model.get("verdict", "UNKNOWN"),
        "composite_score": review_model.get("composite_score", 0),
        "items": items,
        "total_items": len(items),
    }


def render_human_review_checklist_markdown(
    review_model: Dict[str, Any],
    generated_at: str = "deterministic",
) -> str:
    """Generate human review checklist as markdown."""
    lines = [
        "# Human Review Checklist",
        "",
        f"Generated: {generated_at}",
        "",
        f"Verdict: **{review_model.get('verdict', 'UNKNOWN')}**",
        f"Composite Score: {review_model.get('composite_score', 0):.4f}",
        "",
        ADVISORY_DISCLAIMER,
        "",
        "## Checklist",
        "",
    ]
    for i, item in enumerate(CHECKLIST_ITEMS, 1):
        lines.append(f"- [ ] {i}. {item}")

    lines.extend([
        "",
        "---",
        "",
        "release_hold: **HOLD**",
        "",
        "**Advisory only. No auto-promotion. Human review required.**",
        "",
    ])

    return "\n".join(lines)
