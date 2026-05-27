"""Research quality HTML report generator.

Local static HTML. No external resources. No network.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any, Dict, List


ADVISORY_DISCLAIMER = (
    "ADVISORY ONLY — This research output is for analysis purposes only. "
    "It does not constitute trading advice."
)


def generate_html_report(
    quality_data: Dict[str, Any],
    artifacts: List[str] = None,
    generated_at: str = None,
) -> str:
    """Generate deterministic HTML report with no external resources."""
    title = html.escape("Multi-Strategy Research Quality Report")
    disclaimer = html.escape(ADVISORY_DISCLAIMER)
    seed = html.escape(str(quality_data.get('deterministic_seed', 'N/A')))
    hold = html.escape(str(quality_data.get('release_hold', 'HOLD')))
    verdict = html.escape(str(quality_data.get('verdict', 'UNKNOWN')))
    gen_at = html.escape(generated_at or "deterministic")

    parts = [
        "<!DOCTYPE html>",
        "<html><head>",
        f"<title>{title}</title>",
        "<style>body{font-family:monospace;margin:2em;max-width:900px}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px 8px}.warn{color:#c00}.ok{color:#0a0}.hold{background:#ff0;padding:2px 6px}</style>",
        "</head><body>",
        f"<h1>{title}</h1>",
        f"<p><em>{gen_at}</em></p>",
        f"<p>Seed: {seed} | Release Hold: <span class='hold'>{hold}</span></p>",
        f"<p><strong>{disclaimer}</strong></p>",
        f"<h2>Verdict: {verdict}</h2>",
    ]

    # Summary
    summary = quality_data.get("summary", {})
    if summary:
        parts.append("<h2>Summary</h2><table>")
        for k, v in sorted(summary.items()):
            parts.append(f"<tr><th>{html.escape(str(k))}</th><td>{html.escape(str(v))}</td></tr>")
        parts.append("</table>")

    # Warnings
    warnings = quality_data.get("warnings", [])
    if warnings:
        parts.append("<h2>Warnings</h2><ul>")
        for w in warnings:
            parts.append(f"<li class='warn'>{html.escape(str(w))}</li>")
        parts.append("</ul>")

    # Hard blocks
    blocks = quality_data.get("hard_blocks", [])
    if blocks:
        parts.append("<h2>Hard Blocks</h2><ul>")
        for b in blocks:
            parts.append(f"<li class='warn'>{html.escape(str(b))}</li>")
        parts.append("</ul>")

    # Artifacts
    if artifacts:
        parts.append("<h2>Artifacts</h2><ul>")
        for a in sorted(artifacts):
            parts.append(f"<li>{html.escape(a)}</li>")
        parts.append("</ul>")

    parts.extend([
        "<hr>",
        f"<p><small>Advisory only. release_hold={hold}. human_review_required=True.</small></p>",
        "</body></html>",
    ])

    return "\n".join(parts)
