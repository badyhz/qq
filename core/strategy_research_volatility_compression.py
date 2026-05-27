"""Volatility compression breakout strategy research adapter.

Detects low volatility compression followed by expansion breakout.
Pure functions, no I/O, no network, no exchange.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

from core.strategy_research_interface import StrategySignal


@dataclass(frozen=True)
class VolatilityCompressionParams:
    """Parameters for volatility compression breakout adapter."""
    compression_lookback_bars: int = 30
    max_range_pct: float = 0.02
    breakout_lookback_bars: int = 20
    breakout_buffer_pct: float = 0.005
    volume_expansion_ratio: float = 1.5
    cooldown_bars: int = 3
    stop_loss_pct: float = 0.02
    take_profit_rr: float = 2.0


def _is_compressed(
    bars: Sequence[Dict[str, Any]],
    lookback: int,
    max_range_pct: float,
) -> bool:
    """Check if recent bars show compressed (low) volatility."""
    if len(bars) < lookback:
        return False
    window = bars[-lookback:]
    highs = [float(b["high"]) for b in window]
    lows = [float(b["low"]) for b in window]
    max_h = max(highs)
    min_l = min(lows)
    if min_l <= 0:
        return False
    range_pct = (max_h - min_l) / min_l
    return range_pct <= max_range_pct


def generate_volatility_compression_signals(
    bars: Sequence[Dict[str, Any]],
    params: VolatilityCompressionParams,
    strategy_id: str = "volatility_compression",
    symbol: str = "UNKNOWN",
    timeframe: str = "5m",
) -> List[StrategySignal]:
    """Generate volatility compression breakout signals.

    Pure function. No mutation. Deterministic.
    """
    if not bars:
        return []

    min_bars = max(params.compression_lookback_bars, params.breakout_lookback_bars) + 1
    signals: List[StrategySignal] = []
    cooldown_remaining = 0
    signal_counter = 0

    for i in range(min_bars, len(bars)):
        if cooldown_remaining > 0:
            cooldown_remaining -= 1
            continue

        current = bars[i]
        c_close = float(current["close"])
        c_volume = float(current["volume"])

        # Check if recent window was compressed
        compression_window = bars[max(0, i - params.compression_lookback_bars):i]
        if not _is_compressed(compression_window, params.compression_lookback_bars, params.max_range_pct):
            continue

        # Compute breakout level from compressed range
        breakout_window = bars[max(0, i - params.breakout_lookback_bars):i]
        rolling_high = max(float(b["high"]) for b in breakout_window) if breakout_window else 0.0
        rolling_low = min(float(b["low"]) for b in breakout_window) if breakout_window else float("inf")

        # Volume expansion check
        avg_vol = sum(float(b["volume"]) for b in breakout_window) / len(breakout_window) if breakout_window else 0.0
        volume_expanding = (avg_vol > 0 and c_volume / avg_vol >= params.volume_expansion_ratio)

        # LONG breakout above compression
        breakout_level = rolling_high * (1.0 + params.breakout_buffer_pct)
        if c_close > breakout_level and (volume_expanding or params.volume_expansion_ratio <= 1.0):
            confidence = min(1.0, 0.5 + (0.5 if volume_expanding else 0.0))
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
                    "compression_lookback_bars": params.compression_lookback_bars,
                    "max_range_pct": params.max_range_pct,
                    "rolling_high": rolling_high,
                    "rolling_low": rolling_low,
                    "breakout_level": breakout_level,
                    "volume_expanding": volume_expanding,
                    "volume_ratio": round(c_volume / avg_vol, 4) if avg_vol > 0 else 0.0,
                    "bar_index": i,
                },
            ))
            cooldown_remaining = params.cooldown_bars

    return signals


VOLATILITY_COMPRESSION_PARAMETER_SCHEMA = {
    "compression_lookback_bars": {"type": "int", "min": 5, "max": 200, "default": 30},
    "max_range_pct": {"type": "float", "min": 0.001, "max": 0.1, "default": 0.02},
    "breakout_lookback_bars": {"type": "int", "min": 5, "max": 100, "default": 20},
    "breakout_buffer_pct": {"type": "float", "min": 0.001, "max": 0.05, "default": 0.005},
    "volume_expansion_ratio": {"type": "float", "min": 1.0, "max": 5.0, "default": 1.5},
    "cooldown_bars": {"type": "int", "min": 0, "max": 50, "default": 3},
    "stop_loss_pct": {"type": "float", "min": 0.005, "max": 0.1, "default": 0.02},
    "take_profit_rr": {"type": "float", "min": 1.0, "max": 5.0, "default": 2.0},
}
