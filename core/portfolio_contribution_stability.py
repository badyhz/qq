"""Portfolio contribution stability — strategy contribution analysis.

Pure functions. No network.
"""
from __future__ import annotations

from typing import Any, Dict, List


def assess_contribution_stability(
    strategy_contributions: Dict[str, float],
    dominance_threshold: float = 0.7,
) -> Dict[str, Any]:
    """Assess if one strategy dominates portfolio contribution."""
    if not strategy_contributions:
        return {"stable": False, "dominant_strategy": None, "warning": "NO_CONTRIBUTIONS"}

    total = sum(abs(c) for c in strategy_contributions.values())
    if total == 0:
        return {"stable": False, "dominant_strategy": None, "warning": "ZERO_CONTRIBUTION"}

    shares = {k: abs(v) / total for k, v in strategy_contributions.items()}
    dominant = max(shares, key=shares.get)
    dominant_share = shares[dominant]

    stable = dominant_share < dominance_threshold
    warning = "" if stable else f"DOMINANT_STRATEGY:{dominant}={dominant_share:.4f}"

    return {
        "stable": stable,
        "dominant_strategy": dominant,
        "dominant_share": dominant_share,
        "shares": shares,
        "warning": warning,
    }
