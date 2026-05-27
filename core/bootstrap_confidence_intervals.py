"""Bootstrap confidence intervals — CI for expectancy, win-rate, stability.

No network.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from core.research_quality_contract import RELEASE_HOLD_VALUE


def compute_confidence_intervals(
    bootstrap_values: List[float],
    confidence: float = 0.95,
) -> Dict[str, float]:
    """Compute confidence intervals from bootstrap values."""
    if not bootstrap_values:
        return {"lower": 0.0, "upper": 0.0, "median": 0.0, "mean": 0.0, "std": 0.0}

    sorted_vals = sorted(bootstrap_values)
    n = len(sorted_vals)

    alpha = (1 - confidence) / 2
    lower_idx = max(0, int(n * alpha))
    upper_idx = min(n - 1, int(n * (1 - alpha)))

    mean = sum(sorted_vals) / n
    var = sum((v - mean) ** 2 for v in sorted_vals) / n

    return {
        "lower": sorted_vals[lower_idx],
        "upper": sorted_vals[upper_idx],
        "median": sorted_vals[n // 2],
        "mean": mean,
        "std": var ** 0.5,
        "confidence_level": confidence,
    }


def compute_win_rate_ci(
    returns: List[float],
    n_iterations: int = 200,
    seed: int = 424242,
) -> Dict[str, Any]:
    """Compute bootstrap CI for win rate."""
    import random
    rng = random.Random(seed)

    if not returns:
        return {"win_rate": 0.0, "ci_lower": 0.0, "ci_upper": 0.0}

    win_rates = []
    for _ in range(n_iterations):
        sample = [rng.choice(returns) for _ in range(len(returns))]
        wr = sum(1 for r in sample if r > 0) / len(sample)
        win_rates.append(wr)

    ci = compute_confidence_intervals(win_rates)
    return {
        "win_rate": sum(1 for r in returns if r > 0) / len(returns),
        "ci_lower": ci["lower"],
        "ci_upper": ci["upper"],
        "bootstrap_mean": ci["mean"],
        "bootstrap_std": ci["std"],
    }


def compute_expectancy_ci(
    returns: List[float],
    n_iterations: int = 200,
    seed: int = 424242,
) -> Dict[str, Any]:
    """Compute bootstrap CI for expectancy."""
    import random
    rng = random.Random(seed)

    if not returns:
        return {"expectancy": 0.0, "ci_lower": 0.0, "ci_upper": 0.0}

    expectancies = []
    for _ in range(n_iterations):
        sample = [rng.choice(returns) for _ in range(len(returns))]
        exp = sum(sample) / len(sample)
        expectancies.append(exp)

    ci = compute_confidence_intervals(expectancies)
    return {
        "expectancy": sum(returns) / len(returns),
        "ci_lower": ci["lower"],
        "ci_upper": ci["upper"],
        "bootstrap_mean": ci["mean"],
        "bootstrap_std": ci["std"],
    }


def build_bootstrap_confidence_report(
    returns: List[float],
    n_iterations: int = 200,
    seed: int = 424242,
    generated_at: str = None,
) -> Dict:
    """Build bootstrap_confidence_intervals.json."""
    win_rate_ci = compute_win_rate_ci(returns, n_iterations, seed)
    expectancy_ci = compute_expectancy_ci(returns, n_iterations, seed + 1)

    return {
        "schema_version": "1.0.0",
        "generated_by": "bootstrap_confidence_intervals",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "win_rate_ci": win_rate_ci,
        "expectancy_ci": expectancy_ci,
        "n_iterations": n_iterations,
        "warnings": [],
        "hard_blocks": [],
        "verdict": "PASS",
    }
