"""Strategy sparse/noisy handling — detect sparse signals and noisy data.

Pure functions. No network.
"""
from __future__ import annotations

from typing import Any, Dict, List


def assess_signal_quality(
    strategy_id: str,
    signal_count: int,
    total_bars: int,
    min_signal_ratio: float = 0.01,
) -> Dict[str, Any]:
    """Assess signal quality — sparse detection, false confidence prevention."""
    ratio = signal_count / max(total_bars, 1)
    is_sparse = ratio < min_signal_ratio

    warnings = []
    if is_sparse:
        warnings.append(f"SPARSE_SIGNAL:{signal_count}/{total_bars}={ratio:.6f}")
    if signal_count == 0:
        warnings.append("ZERO_SIGNALS")

    return {
        "strategy_id": strategy_id,
        "signal_count": signal_count,
        "total_bars": total_bars,
        "signal_ratio": ratio,
        "is_sparse": is_sparse,
        "sufficient_evidence": not is_sparse and signal_count > 0,
        "warnings": warnings,
    }


def assess_adverse_fixture(
    strategy_id: str,
    base_score: float,
    adverse_score: float,
    degradation_threshold: float = 0.3,
) -> Dict[str, Any]:
    """Assess performance degradation on adverse fixtures."""
    if base_score == 0:
        degradation = 0.0
    else:
        degradation = (base_score - adverse_score) / abs(base_score)

    detected = degradation > degradation_threshold
    return {
        "strategy_id": strategy_id,
        "base_score": base_score,
        "adverse_score": adverse_score,
        "degradation": degradation,
        "degradation_detected": detected,
        "warning": f"ADVERSE_DEGRADATION:{degradation:.4f}" if detected else "",
    }
