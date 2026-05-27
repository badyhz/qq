"""Negative control — random parameter baseline.

Budget-limited. Deterministic with seed. No network.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any, Dict, List

from core.research_quality_contract import RELEASE_HOLD_VALUE


def generate_random_parameter_baseline(
    param_ranges: Dict[str, List[Any]],
    seed: int = 424242,
    budget: int = 120,
) -> Dict[str, Any]:
    """Generate random parameter baseline within budget."""
    rng = random.Random(seed)
    param_names = sorted(param_ranges.keys())

    samples = []
    for i in range(min(budget, 100)):
        params = {}
        for name in param_names:
            values = param_ranges[name]
            params[name] = rng.choice(values)
        samples.append(params)

    return {
        "schema_version": "1.0.0",
        "generated_by": "negative_control_random_parameter",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "baseline_type": "random_parameter",
        "sample_count": len(samples),
        "samples": samples[:10],  # First 10 for inspection
        "score": 0.0,
        "warnings": [],
        "hard_blocks": [],
        "verdict": "PASS",
    }
