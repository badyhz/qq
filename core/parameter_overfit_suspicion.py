"""Parameter overfit suspicion — detect needle-in-haystack peaks.

Pure functions. No network.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class OverfitSuspicion:
    """Overfit suspicion assessment."""
    strategy_id: str
    suspicion_score: float  # 0.0 = no suspicion, 1.0 = highly suspicious
    is_suspicious: bool
    reason: str


def compute_overfit_suspicion(
    strategy_id: str,
    score_grid: List[float],
    peak_threshold: float = 2.0,
) -> OverfitSuspicion:
    """Compute overfit suspicion from parameter grid scores.

    Needle-in-haystack: one score much higher than neighbors.
    """
    if len(score_grid) < 3:
        return OverfitSuspicion(strategy_id, 0.0, False, "Insufficient data")

    scores = [s for s in score_grid if s == s]  # filter NaN
    if not scores:
        return OverfitSuspicion(strategy_id, 1.0, True, "All NaN")

    mean = sum(scores) / len(scores)
    max_score = max(scores)

    if mean == 0:
        ratio = 0
    else:
        ratio = max_score / max(abs(mean), 0.001)

    suspicion = min(ratio / peak_threshold, 1.0) if ratio > 1 else 0.0
    is_suspicious = ratio > peak_threshold

    return OverfitSuspicion(
        strategy_id=strategy_id,
        suspicion_score=suspicion,
        is_suspicious=is_suspicious,
        reason=f"Peak ratio={ratio:.2f}, threshold={peak_threshold}",
    )


def overfit_suspicion_to_dict(o: OverfitSuspicion) -> Dict:
    return {
        "strategy_id": o.strategy_id,
        "suspicion_score": o.suspicion_score,
        "is_suspicious": o.is_suspicious,
        "reason": o.reason,
    }
