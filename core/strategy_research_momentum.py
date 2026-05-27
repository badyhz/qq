"""Momentum continuation strategy research adapter.

Identifies directional continuation after sustained momentum.
Pure functions, no I/O, no network, no exchange.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

from core.strategy_research_interface import StrategySignal


@dataclass(frozen=True)
class MomentumParams:
    """Parameters for momentum continuation adapter."""
    momentum_lookback_bars: int = 30
    min_return_pct: float = 0.02
    ema_fast: int = 10
    ema_slow: int = 50
    min_slope_pct: float = 0.001
    cooldown_bars: int = 3
    stop_loss_pct: float = 0.02
    take_profit_rr: float = 2.0


def _ema(values: List[float], period: int) -> float:
    """Compute exponential moving average of last values."""
    if not values or period <= 0:
        return 0.0
    k = 2.0 / (period + 1)
    ema_val = values[0]
    for v in values[1:]:
        ema_val = v * k + ema_val * (1 - k)
    return ema_val


def _slope(values: List[float], lookback: int) -> float:
    """Compute simple slope (avg change per bar) over lookback."""
    if len(values) < lookback + 1 or lookback <= 0:
        return 0.0
    return (values[-1] - values[-lookback - 1]) / lookback


def generate_momentum_signals(
    bars: Sequence[Dict[str, Any]],
    params: MomentumParams,
    strategy_id: str = "momentum",
    symbol: str = "UNKNOWN",
    timeframe: str = "5m",
) -> List[StrategySignal]:
    """Generate momentum continuation signals from OHLCV bars.

    Pure function. No mutation. Deterministic.
    """
    if not bars:
        return []

    signals: List[StrategySignal] = []
    cooldown_remaining = 0
    signal_counter = 0
    min_bars = max(params.momentum_lookback_bars, params.ema_slow) + 1

    for i in range(min_bars, len(bars)):
        if cooldown_remaining > 0:
            cooldown_remaining -= 1
            continue

        current = bars[i]
        c_close = float(current["close"])

        # Recent return
        past_close = float(bars[i - params.momentum_lookback_bars]["close"])
        if past_close == 0:
            continue
        recent_return = (c_close - past_close) / past_close

        # EMA alignment
        closes_up_to = [float(b["close"]) for b in bars[:i + 1]]
        ema_f = _ema(closes_up_to[-params.ema_slow:], params.ema_fast)
        ema_s = _ema(closes_up_to[-params.ema_slow:], params.ema_slow)

        # Slope confirmation
        slope_val = _slope(closes_up_to, params.momentum_lookback_bars)
        if c_close == 0:
            continue
        slope_pct = slope_val / c_close

        # LONG momentum: positive return, fast EMA > slow EMA, positive slope
        if (recent_return >= params.min_return_pct
                and ema_f > ema_s
                and slope_pct >= params.min_slope_pct):
            confidence = min(1.0, recent_return / (params.min_return_pct * 3))
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
                    "momentum_lookback_bars": params.momentum_lookback_bars,
                    "recent_return_pct": round(recent_return, 6),
                    "ema_fast": round(ema_f, 6),
                    "ema_slow": round(ema_s, 6),
                    "slope_pct": round(slope_pct, 6),
                    "bar_index": i,
                },
            ))
            cooldown_remaining = params.cooldown_bars

    return signals


MOMENTUM_PARAMETER_SCHEMA = {
    "momentum_lookback_bars": {"type": "int", "min": 5, "max": 200, "default": 30},
    "min_return_pct": {"type": "float", "min": 0.001, "max": 0.1, "default": 0.02},
    "ema_fast": {"type": "int", "min": 3, "max": 50, "default": 10},
    "ema_slow": {"type": "int", "min": 10, "max": 200, "default": 50},
    "min_slope_pct": {"type": "float", "min": 0.0, "max": 0.05, "default": 0.001},
    "cooldown_bars": {"type": "int", "min": 0, "max": 50, "default": 3},
    "stop_loss_pct": {"type": "float", "min": 0.005, "max": 0.1, "default": 0.02},
    "take_profit_rr": {"type": "float", "min": 1.0, "max": 5.0, "default": 2.0},
}
