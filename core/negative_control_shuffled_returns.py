"""Negative control — shuffled returns baseline.

Deterministic with seed. No network.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any, Dict, List

from core.research_quality_contract import RELEASE_HOLD_VALUE


def generate_shuffled_returns_baseline(
    returns: List[float],
    seed: int = 424242,
    generated_at: str = None,
) -> Dict[str, Any]:
    """Generate shuffled returns baseline."""
    rng = random.Random(seed)
    shuffled = list(returns)
    rng.shuffle(shuffled)

    total = sum(shuffled)
    mean = total / max(len(shuffled), 1)
    var = sum((r - mean) ** 2 for r in shuffled) / max(len(shuffled), 1)

    return {
        "schema_version": "1.0.0",
        "generated_by": "negative_control_shuffled_returns",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "baseline_type": "shuffled_returns",
        "sample_count": len(shuffled),
        "total_return": total,
        "mean_return": mean,
        "variance": var,
        "score": mean,
        "warnings": [],
        "hard_blocks": [],
        "verdict": "PASS",
    }
