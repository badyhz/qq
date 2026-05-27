"""Strategy robustness lab — per-strategy stress testing.

Pure functions. No network. No exchange.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from core.research_quality_contract import RELEASE_HOLD_VALUE


@dataclass(frozen=True)
class StrategyRobustnessResult:
    """Robustness result for a single strategy."""
    strategy_id: str
    score: float
    trade_count: int
    regime_sensitivity: float
    symbol_sensitivity: float
    timeframe_sensitivity: float
    is_robust: bool
    warnings: Tuple[str, ...]


def assess_strategy_robustness(
    strategy_id: str,
    results: List[Dict[str, Any]],
    min_trades: int = 5,
    min_score: float = 0.0,
) -> StrategyRobustnessResult:
    """Assess robustness of a strategy across its results."""
    if not results:
        return StrategyRobustnessResult(strategy_id, 0.0, 0, 1.0, 1.0, 1.0, False, ("NO_DATA",))

    scores = [r.get("score", 0) for r in results if r.get("score", 0) == r.get("score", 0)]
    trades = [r.get("trade_count", 0) for r in results]
    avg_score = sum(scores) / len(scores) if scores else 0
    total_trades = sum(trades)

    warnings = []
    if total_trades < min_trades:
        warnings.append(f"INSUFFICIENT_TRADES:{total_trades}")
    if avg_score < min_score:
        warnings.append(f"LOW_SCORE:{avg_score:.4f}")

    # Sensitivity: std/mean of scores across different conditions
    if len(scores) > 1:
        mean = sum(scores) / len(scores)
        var = sum((s - mean) ** 2 for s in scores) / len(scores)
        sensitivity = min((var ** 0.5) / max(abs(mean), 0.001), 1.0)
    else:
        sensitivity = 0.5 if len(scores) == 1 else 1.0

    is_robust = len(warnings) == 0 and avg_score >= min_score

    return StrategyRobustnessResult(
        strategy_id=strategy_id,
        score=avg_score,
        trade_count=total_trades,
        regime_sensitivity=sensitivity,
        symbol_sensitivity=sensitivity,
        timeframe_sensitivity=sensitivity,
        is_robust=is_robust,
        warnings=tuple(warnings),
    )


def build_strategy_robustness_report(
    results: List[StrategyRobustnessResult],
    seed: int = 424242,
    generated_at: str = None,
) -> Dict:
    """Build strategy_robustness_report.json."""
    blocks = [r.strategy_id for r in results if not r.is_robust]
    return {
        "schema_version": "1.0.0",
        "generated_by": "strategy_robustness_lab",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "summary": {
            "total_strategies": len(results),
            "robust_count": sum(1 for r in results if r.is_robust),
            "fragile_count": len(blocks),
        },
        "strategies": [
            {
                "strategy_id": r.strategy_id, "score": r.score,
                "trade_count": r.trade_count, "is_robust": r.is_robust,
                "warnings": list(r.warnings),
            }
            for r in sorted(results, key=lambda x: x.strategy_id)
        ],
        "hard_blocks": sorted(blocks),
        "warnings": [],
        "verdict": "FAIL" if blocks else "PASS",
    }
