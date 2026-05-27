"""OOS validation report — out-of-sample stability by split.

Pure functions. No network.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from core.research_quality_contract import RELEASE_HOLD_VALUE


@dataclass(frozen=True)
class OOSSplitMetric:
    """OOS metrics for a single split."""
    split_id: str
    strategy_id: str
    symbol: str
    timeframe: str
    train_score: float
    test_score: float
    degradation: float
    stable: bool
    warning: str


def compute_oos_split_metrics(
    results: List[Dict[str, Any]],
    min_stability: float = 0.5,
) -> Tuple[OOSSplitMetric, ...]:
    """Compute OOS metrics per split."""
    metrics = []
    for r in results:
        train = r.get("train_score", 0)
        test = r.get("test_score", 0)
        degradation = (train - test) / max(abs(train), 0.001) if train != 0 else 0
        stable = degradation < (1 - min_stability)

        metrics.append(OOSSplitMetric(
            split_id=r.get("split_id", ""),
            strategy_id=r.get("strategy_id", ""),
            symbol=r.get("symbol", ""),
            timeframe=r.get("timeframe", ""),
            train_score=train,
            test_score=test,
            degradation=degradation,
            stable=stable,
            warning="" if stable else f"Degradation {degradation:.2%} exceeds threshold",
        ))

    return tuple(metrics)


def build_oos_validation_report(
    metrics: Tuple[OOSSplitMetric, ...],
    seed: int = 424242,
    generated_at: str = None,
) -> Dict:
    """Build oos_validation_report.json artifact."""
    unstable = [m for m in metrics if not m.stable]

    return {
        "schema_version": "1.0.0",
        "generated_by": "oos_validation",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "summary": {
            "total_splits": len(metrics),
            "stable_count": len(metrics) - len(unstable),
            "unstable_count": len(unstable),
        },
        "splits": [
            {
                "split_id": m.split_id, "strategy_id": m.strategy_id,
                "symbol": m.symbol, "timeframe": m.timeframe,
                "train_score": m.train_score, "test_score": m.test_score,
                "degradation": m.degradation, "stable": m.stable,
                "warning": m.warning,
            }
            for m in metrics
        ],
        "warnings": [m.warning for m in unstable if m.warning],
        "hard_blocks": [] if not unstable else ["OOS_INSTABILITY"],
        "verdict": "FAIL" if unstable else "PASS",
    }
