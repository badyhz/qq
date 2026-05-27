"""Research quality closeout — closeout report generator.

Advisory only. No promotion. No network.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from core.research_quality_contract import RELEASE_HOLD_VALUE


ADVISORY_REMINDER = (
    "Research output remains advisory only. No live/testnet/runtime promotion. "
    "release_hold=HOLD. human_review_required=True."
)


def generate_closeout_report(
    verdict: str,
    commit_hash: str = "",
    changed_files: List[str] = None,
    test_summary: Dict[str, Any] = None,
    acceptance_results: Dict[str, Any] = None,
    artifacts: List[str] = None,
    safety_flags: Dict[str, bool] = None,
    seed: int = 424242,
) -> str:
    """Generate closeout markdown report."""
    lines = [
        "# T5201-T9000 Research Quality Gate Closeout",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Seed: {seed}",
        "",
        f"## Verdict: **{verdict}**",
        "",
        ADVISORY_REMINDER,
        "",
    ]

    if commit_hash:
        lines.extend(["## Commit", "", f"`{commit_hash}`", ""])

    if changed_files:
        lines.extend(["## Changed Files", ""])
        for f in sorted(changed_files):
            lines.append(f"- `{f}`")
        lines.append("")

    if test_summary:
        lines.extend(["## Test Summary", ""])
        for k, v in sorted(test_summary.items()):
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    if acceptance_results:
        lines.extend(["## Acceptance Commands", ""])
        for k, v in sorted(acceptance_results.items()):
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    if artifacts:
        lines.extend(["## Required Artifacts", ""])
        for a in sorted(artifacts):
            lines.append(f"- `{a}`")
        lines.append("")

    if safety_flags:
        lines.extend(["## Safety Flags", ""])
        for k, v in sorted(safety_flags.items()):
            lines.append(f"- {k}: {v}")
        lines.append("")

    lines.extend([
        "## Human Review Requirement",
        "",
        "This output requires human review before any promotion decision.",
        "Research is advisory only. No auto-promotion to live/testnet/runtime.",
        "",
        ADVISORY_REMINDER,
        "",
    ])

    return "\n".join(lines)


def build_closeout_data(
    verdict: str,
    seed: int = 424242,
    **kwargs,
) -> Dict:
    """Build closeout data dict for JSON artifact."""
    return {
        "schema_version": "1.0.0",
        "generated_by": "research_quality_closeout",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "verdict": verdict,
        "advisory_reminder": ADVISORY_REMINDER,
        **kwargs,
    }
