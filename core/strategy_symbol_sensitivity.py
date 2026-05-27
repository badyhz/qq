"""Strategy symbol sensitivity — per-strategy symbol diagnostics.

Pure functions. No network.
"""
from __future__ import annotations

from typing import Any, Dict, List


def compute_symbol_sensitivity(
    strategy_id: str,
    symbol_scores: Dict[str, float],
) -> Dict[str, Any]:
    """Compute symbol concentration and sensitivity."""
    if not symbol_scores:
        return {"strategy_id": strategy_id, "concentration": 1.0, "symbols": {}, "warning": "NO_SYMBOL_DATA"}

    scores = list(symbol_scores.values())
    total = sum(abs(s) for s in scores)
    if total == 0:
        concentration = 1.0
    else:
        # HHI-style concentration
        shares = [abs(s) / total for s in scores]
        concentration = sum(s ** 2 for s in shares)

    warnings = []
    if len(symbol_scores) == 1:
        warnings.append("SINGLE_SYMBOL")
    elif concentration > 0.7:
        warnings.append(f"HIGH_CONCENTRATION:{concentration:.4f}")

    return {
        "strategy_id": strategy_id,
        "concentration": concentration,
        "symbols": symbol_scores,
        "warning": "; ".join(warnings) if warnings else "",
    }
