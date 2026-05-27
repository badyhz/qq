"""Research quality markdown report generator.

Advisory-only language. No external assets. No network.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


ADVISORY_DISCLAIMER = (
    "**ADVISORY ONLY** — This research output is for analysis purposes only. "
    "It does not constitute trading advice and must not be used for live trading, "
    "testnet submission, or any form of automated order placement."
)


def generate_markdown_report(
    quality_data: Dict[str, Any],
    artifacts: List[str] = None,
    generated_at: str = None,
) -> str:
    """Generate deterministic markdown report."""
    gen_at = generated_at or "deterministic"
    lines = [
        "# Multi-Strategy Research Quality Report",
        "",
        f"Generated: {gen_at}",
        f"Seed: {quality_data.get('deterministic_seed', 'N/A')}",
        f"Release Hold: {quality_data.get('release_hold', 'HOLD')}",
        "",
        ADVISORY_DISCLAIMER,
        "",
        "## Summary",
        "",
    ]

    # Summary section
    summary = quality_data.get("summary", {})
    for k, v in sorted(summary.items()):
        lines.append(f"- **{k}**: {v}")

    lines.extend(["", "## Verdict", "", f"**{quality_data.get('verdict', 'UNKNOWN')}**", ""])

    # Warnings
    warnings = quality_data.get("warnings", [])
    if warnings:
        lines.extend(["## Warnings", ""])
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    # Hard blocks
    blocks = quality_data.get("hard_blocks", [])
    if blocks:
        lines.extend(["## Hard Blocks", ""])
        for b in blocks:
            lines.append(f"- {b}")
        lines.append("")

    # Safety flags
    lines.extend(["## Safety Flags", ""])
    lines.append(f"- release_hold: {quality_data.get('release_hold', 'HOLD')}")
    lines.append(f"- advisory_only: {quality_data.get('advisory_only', True)}")
    lines.append(f"- human_review_required: {quality_data.get('human_review_required', True)}")
    lines.append("")

    # Artifacts
    if artifacts:
        lines.extend(["## Artifacts", ""])
        for a in sorted(artifacts):
            lines.append(f"- {a}")
        lines.append("")

    return "\n".join(lines)
