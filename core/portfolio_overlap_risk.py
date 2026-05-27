"""Portfolio overlap risk — overlap score and same-bar collision analysis.

No order submission. Advisory only. Pure functions.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from core.research_quality_contract import RELEASE_HOLD_VALUE


@dataclass(frozen=True)
class OverlapResult:
    """Overlap analysis result."""
    strategy_a: str
    strategy_b: str
    overlap_score: float  # 0.0 = no overlap, 1.0 = full overlap
    same_bar_collisions: int
    total_bars: int


def compute_overlap(
    signals_a: List[int],
    signals_b: List[int],
    strategy_a: str = "",
    strategy_b: str = "",
) -> OverlapResult:
    """Compute overlap between two signal series. 1=long, -1=short, 0=flat."""
    n = min(len(signals_a), len(signals_b))
    if n == 0:
        return OverlapResult(strategy_a, strategy_b, 0.0, 0, 0)

    collisions = 0
    same_direction = 0
    for i in range(n):
        if signals_a[i] != 0 and signals_b[i] != 0:
            if signals_a[i] == signals_b[i]:
                same_direction += 1
            collisions += 1

    overlap = collisions / n
    return OverlapResult(strategy_a, strategy_b, overlap, collisions, n)


def build_overlap_risk_report(
    overlaps: List[OverlapResult],
    max_overlap_risk: float = 0.7,
    seed: int = 424242,
    generated_at: str = None,
) -> Dict:
    """Build portfolio_overlap_risk.json."""
    high_overlap = [o for o in overlaps if o.overlap_score > max_overlap_risk]
    blocks = [f"{o.strategy_a}+{o.strategy_b}" for o in high_overlap]

    return {
        "schema_version": "1.0.0",
        "generated_by": "portfolio_overlap_risk",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "summary": {
            "total_pairs": len(overlaps),
            "high_overlap_count": len(high_overlap),
            "max_overlap_score": max((o.overlap_score for o in overlaps), default=0),
        },
        "overlaps": [
            {
                "strategy_a": o.strategy_a, "strategy_b": o.strategy_b,
                "overlap_score": o.overlap_score, "same_bar_collisions": o.same_bar_collisions,
                "total_bars": o.total_bars,
            }
            for o in sorted(overlaps, key=lambda x: -x.overlap_score)
        ],
        "hard_blocks": sorted(blocks),
        "warnings": [],
        "verdict": "FAIL" if blocks else "PASS",
    }
