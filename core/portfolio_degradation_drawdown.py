"""Portfolio degradation and drawdown proxy.

Pure functions. No network.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from core.research_quality_contract import RELEASE_HOLD_VALUE


def compute_drawdown_proxy(equity_curve: List[float]) -> Dict[str, Any]:
    """Compute max drawdown from equity curve."""
    if not equity_curve:
        return {"max_drawdown": 0.0, "max_drawdown_pct": 0.0, "warning": "EMPTY_EQUITY"}

    peak = equity_curve[0]
    max_dd = 0.0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = peak - val
        if dd > max_dd:
            max_dd = dd

    max_dd_pct = max_dd / max(abs(peak), 0.001)
    warning = ""
    if max_dd_pct > 0.2:
        warning = f"HIGH_DRAWDOWN:{max_dd_pct:.4f}"

    return {"max_drawdown": max_dd, "max_drawdown_pct": max_dd_pct, "warning": warning}


def compute_portfolio_degradation(
    train_score: float,
    test_score: float,
    degradation_threshold: float = 0.3,
) -> Dict[str, Any]:
    """Compute portfolio degradation between train and test."""
    if train_score == 0:
        degradation = 0.0
    else:
        degradation = (train_score - test_score) / abs(train_score)

    detected = degradation > degradation_threshold
    return {
        "train_score": train_score,
        "test_score": test_score,
        "degradation": degradation,
        "degradation_detected": detected,
        "warning": f"DEGRADATION:{degradation:.4f}" if detected else "",
    }


def build_portfolio_robustness_report(
    strategy_data: Dict[str, Any],
    drawdown_data: Dict[str, Any],
    seed: int = 424242,
    generated_at: str = None,
) -> Dict:
    """Build portfolio_robustness_report.json."""
    warnings = []
    if drawdown_data.get("warning"):
        warnings.append(drawdown_data["warning"])

    return {
        "schema_version": "1.0.0",
        "generated_by": "portfolio_degradation_drawdown",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "strategy_data": strategy_data,
        "drawdown": drawdown_data,
        "warnings": warnings,
        "hard_blocks": [],
        "verdict": "PASS",
    }
