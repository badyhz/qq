"""Regime research segmentation — trend/chop/volatility buckets.

Deterministic. No network.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from core.research_quality_contract import RELEASE_HOLD_VALUE


def classify_regime(
    returns: List[float],
    lookback: int = 20,
) -> str:
    """Classify market regime from recent returns."""
    if len(returns) < lookback:
        return "AMBIGUOUS"

    recent = returns[-lookback:]
    mean = sum(recent) / len(recent)
    var = sum((r - mean) ** 2 for r in recent) / len(recent)
    vol = var ** 0.5

    # Trend: strong directional move
    abs_mean = abs(mean)
    if abs_mean > vol * 0.5 and abs_mean > 0.001:
        return "TREND"

    # Chop: low vol, no direction
    if vol < 0.005:
        return "CHOP"

    # Volatile: high vol
    if vol > 0.02:
        return "VOLATILE"

    return "CHOP"


def segment_by_regime(
    returns: List[float],
    lookback: int = 20,
) -> Dict[str, List[float]]:
    """Segment returns into regime buckets."""
    regimes = {"TREND": [], "CHOP": [], "VOLATILE": [], "AMBIGUOUS": []}

    for i in range(lookback, len(returns)):
        window = returns[max(0, i - lookback):i]
        regime = classify_regime(window, lookback)
        regimes[regime].append(returns[i])

    return regimes


def build_regime_breakdown(
    strategy_id: str,
    returns: List[float],
    lookback: int = 20,
    seed: int = 424242,
    generated_at: str = None,
) -> Dict:
    """Build regime_breakdown.json."""
    regimes = segment_by_regime(returns, lookback)

    regime_scores = {}
    for name, vals in regimes.items():
        if vals:
            regime_scores[name] = {
                "count": len(vals),
                "mean_return": sum(vals) / len(vals),
                "total_return": sum(vals),
            }
        else:
            regime_scores[name] = {"count": 0, "mean_return": 0, "total_return": 0}

    # Check regime concentration
    total = sum(len(v) for v in regimes.values())
    concentrations = {k: len(v) / max(total, 1) for k, v in regimes.items()}
    max_conc = max(concentrations.values()) if concentrations else 0

    warnings = []
    if max_conc > 0.8:
        dominant = max(concentrations, key=concentrations.get)
        warnings.append(f"REGIME_CONCENTRATION:{dominant}={max_conc:.4f}")

    return {
        "schema_version": "1.0.0",
        "generated_by": "regime_research_segmentation",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "strategy_id": strategy_id,
        "regime_scores": regime_scores,
        "concentrations": concentrations,
        "total_observations": total,
        "warnings": warnings,
        "hard_blocks": [],
        "verdict": "PASS",
    }
