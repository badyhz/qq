"""Negative control — inverted signal baseline.

No order semantics. Pure functions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from core.research_quality_contract import RELEASE_HOLD_VALUE


def generate_inverted_signal_baseline(
    signals: List[int],
    returns: List[float],
    seed: int = 424242,
    generated_at: str = None,
) -> Dict[str, Any]:
    """Generate inverted signal baseline — take opposite positions."""
    inverted = [-s for s in signals]
    n = min(len(inverted), len(returns))

    inverted_returns = []
    for i in range(n):
        if inverted[i] != 0:
            inverted_returns.append(returns[i] * (-1 if signals[i] != 0 else 0))
        else:
            inverted_returns.append(0.0)

    total = sum(inverted_returns)
    mean = total / max(len(inverted_returns), 1)

    return {
        "schema_version": "1.0.0",
        "generated_by": "negative_control_inverted_signal",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "baseline_type": "inverted_signal",
        "total_bars": len(signals),
        "inverted_returns_count": len(inverted_returns),
        "total_return": total,
        "mean_return": mean,
        "score": mean,
        "warnings": [],
        "hard_blocks": [],
        "verdict": "PASS",
    }
