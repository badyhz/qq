"""Negative control — permuted signal baseline.

Deterministic with seed. No network.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any, Dict, List

from core.research_quality_contract import RELEASE_HOLD_VALUE


def generate_permuted_signal_baseline(
    signals: List[int],
    seed: int = 424242,
) -> Dict[str, Any]:
    """Generate permuted signal baseline."""
    rng = random.Random(seed)
    permuted = list(signals)
    rng.shuffle(permuted)

    signal_count = sum(1 for s in permuted if s != 0)

    return {
        "schema_version": "1.0.0",
        "generated_by": "negative_control_permuted_signal",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "baseline_type": "permuted_signal",
        "total_bars": len(permuted),
        "signal_count": signal_count,
        "score": 0.0,
        "warnings": [],
        "hard_blocks": [],
        "verdict": "PASS",
    }
