"""Strategy timeframe sensitivity — per-strategy timeframe diagnostics.

Pure functions. No network.
"""
from __future__ import annotations

from typing import Any, Dict


def compute_timeframe_sensitivity(
    strategy_id: str,
    timeframe_scores: Dict[str, float],
) -> Dict[str, Any]:
    """Compute timeframe sensitivity."""
    if not timeframe_scores:
        return {"strategy_id": strategy_id, "sensitivity": 1.0, "timeframes": {}, "warning": "NO_TIMEFRAME_DATA"}

    scores = list(timeframe_scores.values())
    mean = sum(scores) / len(scores)
    var = sum((s - mean) ** 2 for s in scores) / len(scores)
    sensitivity = min((var ** 0.5) / max(abs(mean), 0.001), 1.0)

    return {
        "strategy_id": strategy_id,
        "sensitivity": sensitivity,
        "timeframes": timeframe_scores,
        "warning": "" if sensitivity < 0.5 else f"HIGH_TIMEFRAME_SENSITIVITY:{sensitivity:.4f}",
    }
