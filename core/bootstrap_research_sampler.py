"""Bootstrap research sampler — deterministic bootstrap with seed.

Same seed = same samples. No network.
"""
from __future__ import annotations

import random
from typing import Any, List, Tuple


def deterministic_bootstrap_sample(
    data: List[float],
    n_iterations: int = 200,
    seed: int = 424242,
    sample_fraction: float = 1.0,
) -> Tuple[List[List[float]], int]:
    """Generate deterministic bootstrap resamples.

    Returns (resamples, seed_used).
    """
    rng = random.Random(seed)
    n = max(1, int(len(data) * sample_fraction))

    resamples = []
    for _ in range(n_iterations):
        sample = [rng.choice(data) for _ in range(n)]
        resamples.append(sample)

    return resamples, seed


def compute_bootstrap_statistic(
    resamples: List[List[float]],
    stat_fn=None,
) -> List[float]:
    """Compute statistic on each resample."""
    if stat_fn is None:
        stat_fn = lambda x: sum(x) / len(x) if x else 0.0

    return [stat_fn(s) for s in resamples]
