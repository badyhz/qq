"""Strategy entry/exit diagnostics — entry/exit behavior analysis.

No order placement semantics. Advisory only. Pure functions.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def compute_entry_exit_diagnostics(
    strategy_id: str,
    trades: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute entry/exit diagnostics from trade records."""
    if not trades:
        return {
            "strategy_id": strategy_id,
            "trade_count": 0,
            "avg_hold_bars": 0,
            "exit_type_distribution": {},
            "warnings": ["NO_TRADES"],
        }

    hold_bars = []
    exit_types = {}
    for t in trades:
        hb = t.get("hold_bars", t.get("duration", 0))
        hold_bars.append(hb)
        et = t.get("exit_type", "unknown")
        exit_types[et] = exit_types.get(et, 0) + 1

    avg_hold = sum(hold_bars) / len(hold_bars) if hold_bars else 0

    warnings = []
    if exit_types.get("no_exit", 0) > len(trades) * 0.5:
        warnings.append("HIGH_NO_EXIT_RATE")
    if avg_hold == 0:
        warnings.append("ZERO_HOLD_TIME")

    return {
        "strategy_id": strategy_id,
        "trade_count": len(trades),
        "avg_hold_bars": avg_hold,
        "exit_type_distribution": exit_types,
        "warnings": warnings,
    }
