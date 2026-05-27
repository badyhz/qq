"""Portfolio crowding and exposure concentration.

Pure functions. No network.
"""
from __future__ import annotations

from typing import Any, Dict


def compute_crowding_score(
    strategy_weights: Dict[str, float],
) -> Dict[str, Any]:
    """Compute crowding score (HHI of weights)."""
    if not strategy_weights:
        return {"crowding_score": 1.0, "warning": "NO_STRATEGIES"}

    weights = list(strategy_weights.values())
    total = sum(abs(w) for w in weights)
    if total == 0:
        return {"crowding_score": 1.0, "warning": "ZERO_WEIGHTS"}

    shares = [abs(w) / total for w in weights]
    hhi = sum(s ** 2 for s in shares)

    warning = ""
    if hhi > 0.5:
        warning = f"HIGH_CROWDING:{hhi:.4f}"

    return {"crowding_score": hhi, "warning": warning}


def compute_exposure_concentration(
    symbol_exposures: Dict[str, float],
) -> Dict[str, Any]:
    """Compute exposure concentration across symbols."""
    if not symbol_exposures:
        return {"concentration": 1.0, "warning": "NO_EXPOSURES"}

    total = sum(abs(e) for e in symbol_exposures.values())
    if total == 0:
        return {"concentration": 1.0, "warning": "ZERO_EXPOSURE"}

    shares = [abs(e) / total for e in symbol_exposures.values()]
    hhi = sum(s ** 2 for s in shares)

    warning = ""
    if hhi > 0.5:
        warning = f"HIGH_EXPOSURE_CONCENTRATION:{hhi:.4f}"

    return {"concentration": hhi, "warning": warning}
