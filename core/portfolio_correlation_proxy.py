"""Portfolio correlation proxy — estimate correlation from return series.

Pure functions. No network.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from core.research_quality_contract import RELEASE_HOLD_VALUE


def compute_correlation_proxy(
    returns_a: List[float],
    returns_b: List[float],
) -> float:
    """Compute Pearson correlation proxy between two return series."""
    n = min(len(returns_a), len(returns_b))
    if n < 2:
        return 0.0

    a = returns_a[:n]
    b = returns_b[:n]

    mean_a = sum(a) / n
    mean_b = sum(b) / n

    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n)) / n
    var_a = sum((x - mean_a) ** 2 for x in a) / n
    var_b = sum((x - mean_b) ** 2 for x in b) / n

    denom = (var_a * var_b) ** 0.5
    if denom == 0:
        return 0.0
    return cov / denom


def compute_correlation_matrix(
    strategy_returns: Dict[str, List[float]],
) -> Dict[str, Dict[str, float]]:
    """Compute pairwise correlation matrix."""
    ids = sorted(strategy_returns.keys())
    matrix = {}
    for a in ids:
        matrix[a] = {}
        for b in ids:
            if a == b:
                matrix[a][b] = 1.0
            elif b in matrix and a in matrix[b]:
                matrix[a][b] = matrix[b][a]
            else:
                matrix[a][b] = compute_correlation_proxy(
                    strategy_returns[a], strategy_returns[b]
                )
    return matrix


def build_correlation_report(
    strategy_returns: Dict[str, List[float]],
    seed: int = 424242,
    generated_at: str = None,
) -> Dict:
    """Build correlation_proxy_report.json."""
    matrix = compute_correlation_matrix(strategy_returns)
    high_corr_pairs = []
    ids = sorted(matrix.keys())
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            corr = matrix[a][b]
            if abs(corr) > 0.7:
                high_corr_pairs.append({"strategy_a": a, "strategy_b": b, "correlation": corr})

    return {
        "schema_version": "1.0.0",
        "generated_by": "portfolio_correlation_proxy",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "correlation_matrix": matrix,
        "high_correlation_pairs": high_corr_pairs,
        "warnings": ["HIGH_CORRELATION" if high_corr_pairs else ""],
        "hard_blocks": [],
        "verdict": "PASS",
    }
