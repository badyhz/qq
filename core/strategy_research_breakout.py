"""Breakout strategy research adapter — reuses safe local breakout logic.

Pure functions, no I/O, no network, no exchange.
Wraps existing offline breakout signal logic into the StrategySignal format.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

from core.strategy_research_interface import StrategySignal


# --- Default breakout parameters ---

@dataclass(frozen=True)
class BreakoutResearchParams:
    """Parameters for the breakout research adapter."""
    lookback_bars: int = 20
    breakout_buffer_pct: float = 0.005
    min_body_pct: float = 0.5
    cooldown_bars: int = 3
    stop_loss_pct: float = 0.02
    take_profit_rr: float = 2.0


# --- Bar type (dict-based for flexibility) ---

def _validate_bars(bars: Sequence[Dict[str, Any]]) -> None:
    """Validate that bars have required fields."""
    if not bars:
        return
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    for i, bar in enumerate(bars[:1]):
        missing = required - set(bar.keys())
        if missing:
            raise ValueError(f"bar[{i}] missing fields: {missing}")


def generate_breakout_signals(
    bars: Sequence[Dict[str, Any]],
    params: BreakoutResearchParams,
    strategy_id: str = "breakout",
    symbol: str = "UNKNOWN",
    timeframe: str = "5m",
) -> List[StrategySignal]:
    """Generate breakout signals from OHLCV bars.

    Pure function. No mutation of input bars. No side effects.
    Deterministic output ordering.
    """
    if not bars:
        return []

    _validate_bars(bars)

    signals: List[StrategySignal] = []
    cooldown_remaining = 0
    signal_counter = 0

    for i in range(params.lookback_bars, len(bars)):
        if cooldown_remaining > 0:
            cooldown_remaining -= 1
            continue

        current = bars[i]
        c_close = float(current["close"])
        c_high = float(current["high"])
        c_low = float(current["low"])
        c_volume = float(current["volume"])

        # Compute rolling high/low over lookback
        window = bars[max(0, i - params.lookback_bars):i]
        if not window:
            continue

        rolling_high = max(float(b["high"]) for b in window)
        rolling_low = min(float(b["low"]) for b in window)

        # Compute avg volume
        avg_vol = sum(float(b["volume"]) for b in window) / len(window) if window else 0.0

        # Body percentage
        body = abs(c_close - float(current["open"]))
        range_size = c_high - c_low if c_high != c_low else 1.0
        body_pct = body / range_size

        # LONG breakout: close above rolling high + buffer
        breakout_level_up = rolling_high * (1.0 + params.breakout_buffer_pct)
        if c_close > breakout_level_up and body_pct >= params.min_body_pct:
            confidence = min(1.0, (c_close - breakout_level_up) / (breakout_level_up * 0.01) + 0.3)
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
                    "rolling_high": rolling_high,
                    "breakout_level": breakout_level_up,
                    "volume_ratio": round(c_volume / avg_vol, 4) if avg_vol > 0 else 0.0,
                    "bar_index": i,
                },
            ))
            cooldown_remaining = params.cooldown_bars
            continue

        # SHORT breakout: close below rolling low - buffer
        breakout_level_down = rolling_low * (1.0 - params.breakout_buffer_pct)
        if c_close < breakout_level_down and body_pct >= params.min_body_pct:
            confidence = min(1.0, (breakout_level_down - c_close) / (breakout_level_down * 0.01) + 0.3)
            signal_counter += 1
            signals.append(StrategySignal(
                signal_id=f"{strategy_id}_sig_{signal_counter:06d}",
                strategy_id=strategy_id,
                symbol=symbol,
                timeframe=timeframe,
                timestamp=float(current["timestamp"]),
                side="SHORT",
                entry_reference_price=c_close,
                confidence=round(confidence, 4),
                metadata={
                    "lookback_bars": params.lookback_bars,
                    "rolling_low": rolling_low,
                    "breakout_level": breakout_level_down,
                    "volume_ratio": round(c_volume / avg_vol, 4) if avg_vol > 0 else 0.0,
                    "bar_index": i,
                },
            ))
            cooldown_remaining = params.cooldown_bars

    return signals


# --- Schema for registry ---

BREAKOUT_PARAMETER_SCHEMA = {
    "lookback_bars": {"type": "int", "min": 5, "max": 100, "default": 20},
    "breakout_buffer_pct": {"type": "float", "min": 0.001, "max": 0.05, "default": 0.005},
    "min_body_pct": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.5},
    "cooldown_bars": {"type": "int", "min": 0, "max": 50, "default": 3},
    "stop_loss_pct": {"type": "float", "min": 0.005, "max": 0.1, "default": 0.02},
    "take_profit_rr": {"type": "float", "min": 1.0, "max": 5.0, "default": 2.0},
}
