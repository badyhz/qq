"""Negative control — random strategy baseline.

Deterministic with seed. No network.
"""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timezone
from typing import Any, Dict, List

from core.research_quality_contract import RELEASE_HOLD_VALUE


def generate_random_strategy_baseline(
    total_bars: int,
    seed: int = 424242,
    n_trades_range: tuple = (5, 50),
    generated_at: str = None,
) -> Dict[str, Any]:
    """Generate random strategy baseline with deterministic seed."""
    rng = random.Random(seed)

    n_trades = rng.randint(*n_trades_range) if total_bars > 10 else 0
    trades = []
    for i in range(n_trades):
        entry = rng.randint(0, max(total_bars - 10, 1))
        max_exit = max(1, min(10, total_bars - entry))
        exit_bar = entry + rng.randint(1, max_exit)
        pnl = rng.gauss(0, 0.1)
        trades.append({"entry": entry, "exit": exit_bar, "pnl": pnl})

    total_pnl = sum(t["pnl"] for t in trades)
    avg_pnl = total_pnl / max(n_trades, 1)

    return {
        "schema_version": "1.0.0",
        "generated_by": "negative_control_random_strategy",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "baseline_type": "random_strategy",
        "total_bars": total_bars,
        "trade_count": n_trades,
        "total_pnl": total_pnl,
        "avg_pnl": avg_pnl,
        "score": avg_pnl,
        "warnings": [],
        "hard_blocks": [],
        "verdict": "PASS",
    }
