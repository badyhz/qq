"""Strategy regime sensitivity — per-strategy regime diagnostics.

Pure functions. No network.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def compute_regime_sensitivity(
    strategy_id: str,
    regime_scores: Dict[str, float],
) -> Dict[str, Any]:
    """Compute regime sensitivity for a strategy."""
    if not regime_scores:
        return {"strategy_id": strategy_id, "sensitivity": 1.0, "regimes": {}, "warning": "NO_REGIME_DATA"}

    scores = list(regime_scores.values())
    mean = sum(scores) / len(scores)
    var = sum((s - mean) ** 2 for s in scores) / len(scores)
    sensitivity = min((var ** 0.5) / max(abs(mean), 0.001), 1.0)

    return {
        "strategy_id": strategy_id,
        "sensitivity": sensitivity,
        "regimes": regime_scores,
        "warning": "" if sensitivity < 0.5 else f"HIGH_REGIME_SENSITIVITY:{sensitivity:.4f}",
    }
