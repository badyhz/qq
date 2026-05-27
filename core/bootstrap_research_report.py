"""Bootstrap research report — worst-case percentile and stability.

No network.
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from typing import Any, Dict, List

from core.research_quality_contract import RELEASE_HOLD_VALUE


def compute_worst_case_percentile(
    bootstrap_values: List[float],
    percentile: float = 5.0,
) -> float:
    """Compute worst-case percentile from bootstrap values."""
    if not bootstrap_values:
        return 0.0
    sorted_vals = sorted(bootstrap_values)
    idx = max(0, int(len(sorted_vals) * percentile / 100))
    return sorted_vals[idx]


def compute_resampling_stability(
    bootstrap_values: List[float],
) -> Dict[str, Any]:
    """Compute stability metrics from bootstrap values."""
    if not bootstrap_values:
        return {"stable": False, "cv": 1.0, "warning": "NO_DATA"}

    mean = sum(bootstrap_values) / len(bootstrap_values)
    var = sum((v - mean) ** 2 for v in bootstrap_values) / len(bootstrap_values)
    std = var ** 0.5
    cv = std / max(abs(mean), 0.001)

    stable = cv < 0.5
    return {
        "stable": stable,
        "cv": cv,
        "mean": mean,
        "std": std,
        "warning": "" if stable else f"HIGH_VARIABILITY:{cv:.4f}",
    }


def build_bootstrap_report(
    returns: List[float],
    n_iterations: int = 200,
    seed: int = 424242,
    safety_threshold: float = -0.1,
    generated_at: str = None,
) -> Dict:
    """Build bootstrap_report.json."""
    rng = random.Random(seed)

    if not returns:
        return {
            "schema_version": "1.0.0", "generated_by": "bootstrap_research_report",
            "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
            "deterministic_seed": seed, "release_hold": RELEASE_HOLD_VALUE,
            "advisory_only": True, "human_review_required": True,
            "warnings": ["NO_DATA"], "hard_blocks": ["NO_DATA"], "verdict": "FAIL",
        }

    means = []
    for _ in range(n_iterations):
        sample = [rng.choice(returns) for _ in range(len(returns))]
        means.append(sum(sample) / len(sample))

    wc5 = compute_worst_case_percentile(means, 5.0)
    wc1 = compute_worst_case_percentile(means, 1.0)
    stability = compute_resampling_stability(means)

    blocks = []
    warnings = []
    if wc5 < safety_threshold:
        blocks.append(f"WORST_CASE_BELOW_THRESHOLD:{wc5:.4f}")
    if not stability["stable"]:
        warnings.append(stability["warning"])

    return {
        "schema_version": "1.0.0",
        "generated_by": "bootstrap_research_report",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "n_iterations": n_iterations,
        "sample_count": len(returns),
        "bootstrap_mean": sum(means) / len(means),
        "worst_case_5pct": wc5,
        "worst_case_1pct": wc1,
        "stability": stability,
        "warnings": warnings,
        "hard_blocks": blocks,
        "verdict": "FAIL" if blocks else "PASS",
    }
