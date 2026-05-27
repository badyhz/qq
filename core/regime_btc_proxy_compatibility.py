"""Regime BTC proxy compatibility — check BTC proxy regime alignment.

Offline fixture only. No network. No Binance.
"""
from __future__ import annotations

from typing import Any, Dict


def check_btc_proxy_compatibility(
    strategy_regimes: Dict[str, float],
    btc_regimes: Dict[str, float],
) -> Dict[str, Any]:
    """Check if strategy regime distribution aligns with BTC proxy."""
    if not btc_regimes:
        return {
            "compatible": True,
            "warning": "NO_BTC_PROXY_DATA",
            "offline_only": True,
        }

    all_regimes = set(list(strategy_regimes.keys()) + list(btc_regimes.keys()))
    max_diff = 0
    for regime in all_regimes:
        s = strategy_regimes.get(regime, 0)
        b = btc_regimes.get(regime, 0)
        diff = abs(s - b)
        max_diff = max(max_diff, diff)

    compatible = max_diff < 0.3
    return {
        "compatible": compatible,
        "max_distribution_diff": max_diff,
        "warning": "" if compatible else f"BTC_PROXY_MISMATCH:{max_diff:.4f}",
        "offline_only": True,
    }
