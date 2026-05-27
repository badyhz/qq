"""Mean reversion strategy research adapter.

Detects stretched moves away from rolling mean using z-score.
Pure functions, no I/O, no network, no exchange.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

from core.strategy_research_interface import StrategySignal


@dataclass(frozen=True)
class MeanReversionParams:
    """Parameters for the mean reversion research adapter."""
    lookback_bars: int = 50
    zscore_entry: float = 2.0
    zscore_exit: float = 0.5
    min_volume_ratio: float = 1.0
    cooldown_bars: int = 5
    stop_loss_pct: float = 0.02
    take_profit_rr: float = 2.0


def _mean(values: List[float]) -> float:
    """Compute mean of a list."""
    return sum(values) / len(values) if values else 0.0


def _std(values: List[float]) -> float:
    """Compute population std of a list."""
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / len(values))


def generate_mean_reversion_signals(
    bars: Sequence[Dict[str, Any]],
    params: MeanReversionParams,
    strategy_id: str = "mean_reversion",
    symbol: str = "UNKNOWN",
    timeframe: str = "5m",
) -> List[StrategySignal]:
    """Generate mean reversion signals from OHLCV bars.

    Pure function. No mutation of input bars. Deterministic.
    LONG signal when price drops below mean by z-score threshold.
    """
    if not bars:
        return []

    signals: List[StrategySignal] = []
    cooldown_remaining = 0
    signal_counter = 0

    for i in range(params.lookback_bars, len(bars)):
        if cooldown_remaining > 0:
            cooldown_remaining -= 1
            continue

        current = bars[i]
        c_close = float(current["close"])
        c_volume = float(current["volume"])

        # Compute rolling stats
        window = bars[max(0, i - params.lookback_bars):i]
        closes = [float(b["close"]) for b in window]
        volumes = [float(b["volume"]) for b in window]

        mean_c = _mean(closes)
        std_c = _std(closes)
        avg_vol = _mean(volumes)

        if std_c == 0:
            continue

        # Volume filter
        if avg_vol > 0 and c_volume / avg_vol < params.min_volume_ratio:
            continue

        zscore = (c_close - mean_c) / std_c

        # LONG: price dropped below mean
        if zscore <= -params.zscore_entry:
            confidence = min(1.0, abs(zscore) / (params.zscore_entry * 2))
            signal_counter += 1
            signals.append(StrategySignal(
                signal_id=f"{strategy_id}_sig_{signal_counter:06d}",
                strategy_id=strategy_id,
                symbol=symbol,
                timeframe=timeframe,
                timestamp=float(current["timestamp"]),
                side="LONG",
                entry_reference_price=c_close,
                confidence=round(confidence, 4),
                metadata={
                    "lookback_bars": params.lookback_bars,
                    "zscore": round(zscore, 4),
                    "rolling_mean": round(mean_c, 6),
                    "rolling_std": round(std_c, 6),
                    "bar_index": i,
                },
            ))
            cooldown_remaining = params.cooldown_bars
            continue

        # SHORT: price rose above mean (if short declared)
        # Note: LONG-only by default; SHORT only if explicitly supported
        # Skipping SHORT for safety — declare LONG-only

    return signals


MEAN_REVERSION_PARAMETER_SCHEMA = {
    "lookback_bars": {"type": "int", "min": 5, "max": 200, "default": 50},
    "zscore_entry": {"type": "float", "min": 1.0, "max": 4.0, "default": 2.0},
    "zscore_exit": {"type": "float", "min": 0.0, "max": 2.0, "default": 0.5},
    "min_volume_ratio": {"type": "float", "min": 0.5, "max": 5.0, "default": 1.0},
    "cooldown_bars": {"type": "int", "min": 0, "max": 50, "default": 5},
    "stop_loss_pct": {"type": "float", "min": 0.005, "max": 0.1, "default": 0.02},
    "take_profit_rr": {"type": "float", "min": 1.0, "max": 5.0, "default": 2.0},
}
