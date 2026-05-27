"""Negative control report — margin engine and report builder.

Pure functions. No network.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from core.research_quality_contract import RELEASE_HOLD_VALUE


def evaluate_negative_control_margin(
    strategy_score: float,
    control_scores: Dict[str, float],
    min_margin: float = 0.10,
) -> Dict[str, Any]:
    """Evaluate if real strategy beats all controls by min_margin.

    When both strategy and control have zero score (no signal), margin passes.
    """
    margins = {}
    passes = True

    for control_name, control_score in sorted(control_scores.items()):
        margin = strategy_score - control_score
        margins[control_name] = margin
        # If both are zero (no signal), consider it a tie (pass)
        both_zero = abs(strategy_score) < 1e-9 and abs(control_score) < 1e-9
        if margin < min_margin and not both_zero:
            passes = False

    return {
        "strategy_score": strategy_score,
        "control_scores": control_scores,
        "margins": margins,
        "min_margin": min_margin,
        "passes": passes,
        "warning": "" if passes else f"INSUFFICIENT_MARGIN:{min(margins.values()):.4f}",
    }


def build_negative_control_report(
    strategy_id: str,
    strategy_score: float,
    baselines: Dict[str, Dict[str, Any]],
    min_margin: float = 0.10,
    seed: int = 424242,
    generated_at: str = None,
) -> Dict:
    """Build negative_control_report.json."""
    control_scores = {}
    for name, baseline in baselines.items():
        control_scores[name] = baseline.get("score", 0.0)

    margin_result = evaluate_negative_control_margin(strategy_score, control_scores, min_margin)

    blocks = []
    if not margin_result["passes"]:
        blocks.append("INSUFFICIENT_NEGATIVE_CONTROL_MARGIN")

    return {
        "schema_version": "1.0.0",
        "generated_by": "negative_control_report",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "strategy_id": strategy_id,
        "strategy_score": strategy_score,
        "control_scores": control_scores,
        "margins": margin_result["margins"],
        "min_margin": min_margin,
        "passes_all_controls": margin_result["passes"],
        "baselines": baselines,
        "warnings": [margin_result["warning"]] if margin_result["warning"] else [],
        "hard_blocks": blocks,
        "verdict": "FAIL" if blocks else "PASS",
    }
