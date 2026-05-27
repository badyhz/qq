"""Parameter fragility report — detect fragile parameter regimes.

Pure functions. No network.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from core.research_quality_contract import RELEASE_HOLD_VALUE


@dataclass(frozen=True)
class FragilityResult:
    """Fragility assessment for a parameter neighborhood."""
    strategy_id: str
    fragility_score: float  # 0.0 = robust, 1.0 = fragile
    is_fragile: bool
    reason: str
    neighborhood_scores: Tuple[float, ...]


def compute_fragility(
    strategy_id: str,
    base_score: float,
    neighborhood_scores: List[float],
    fragility_threshold: float = 0.4,
) -> FragilityResult:
    """Compute fragility score from neighborhood perturbation scores."""
    if not neighborhood_scores:
        return FragilityResult(strategy_id, 1.0, True, "No neighborhood data", ())

    # Fragility = coefficient of variation of neighborhood scores
    scores = [s for s in neighborhood_scores if s == s]  # filter NaN
    if not scores:
        return FragilityResult(strategy_id, 1.0, True, "All NaN scores", ())

    mean = sum(scores) / len(scores)
    if mean == 0:
        variance = 0
    else:
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)

    std = variance ** 0.5
    cv = std / max(abs(mean), 0.001)
    fragility = min(cv, 1.0)

    is_fragile = fragility > fragility_threshold
    reason = f"CV={cv:.4f}, threshold={fragility_threshold}"
    if is_fragile:
        reason = f"Fragile: {reason}"

    return FragilityResult(strategy_id, fragility, is_fragile, reason, tuple(neighborhood_scores))


def build_fragility_report(
    results: List[FragilityResult],
    seed: int = 424242,
    generated_at: str = None,
) -> Dict:
    """Build parameter_fragility_report.json."""
    blocks = [r.strategy_id for r in results if r.is_fragile]
    return {
        "schema_version": "1.0.0",
        "generated_by": "parameter_fragility_report",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "summary": {
            "total_strategies": len(results),
            "fragile_count": len(blocks),
            "robust_count": len(results) - len(blocks),
        },
        "results": [
            {
                "strategy_id": r.strategy_id,
                "fragility_score": r.fragility_score,
                "is_fragile": r.is_fragile,
                "reason": r.reason,
            }
            for r in sorted(results, key=lambda x: x.strategy_id)
        ],
        "hard_blocks": sorted(blocks),
        "warnings": [],
        "verdict": "FAIL" if blocks else "PASS",
    }
