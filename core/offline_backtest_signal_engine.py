"""Offline backtest signal engine. Pure functions, no I/O.

Detects breakout signals from bar data using parameter configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Sequence


class SignalType(Enum):
    LONG_BREAKOUT = "LONG_BREAKOUT"


@dataclass(frozen=True)
class Signal:
    """Frozen breakout signal."""

    signal_id: str
    bar_index: int
    signal_type: SignalType
    entry_price: float
    timestamp: object
    lookback_high: float
    body_pct: float

    def __post_init__(self) -> None:
        if self.bar_index < 0:
            raise ValueError(f"bar_index must be >= 0, got {self.bar_index}")
        if self.entry_price <= 0:
            raise ValueError(f"entry_price must be > 0, got {self.entry_price}")
        if self.lookback_high <= 0:
            raise ValueError(f"lookback_high must be > 0, got {self.lookback_high}")


def is_range_high_breakout(bar: dict, lookback_high: float, buffer_pct: float) -> bool:
    """Return True if bar's high exceeds lookback_high by the buffer percentage."""
    if lookback_high <= 0:
        return False
    threshold = lookback_high * (1.0 + buffer_pct)
    return bar["high"] >= threshold


def check_min_body_pct(bar: dict, min_body_pct: float) -> bool:
    """Return True if bar's body (|close - open|) as pct of high-low range meets minimum."""
    high_low_range = bar["high"] - bar["low"]
    if high_low_range <= 0:
        return False
    body = abs(bar["close"] - bar["open"])
    body_pct = body / high_low_range
    return body_pct >= min_body_pct


def _compute_lookback_high(bars: Sequence[dict], current_index: int, lookback_bars: int) -> float:
    """Compute the highest high over the lookback window ending before current_index."""
    start = max(0, current_index - lookback_bars)
    if start >= current_index:
        return 0.0
    return max(b["high"] for b in bars[start:current_index])


def _compute_body_pct(bar: dict) -> float:
    """Compute body percentage of a bar."""
    high_low_range = bar["high"] - bar["low"]
    if high_low_range <= 0:
        return 0.0
    return abs(bar["close"] - bar["open"]) / high_low_range


def detect_breakout_signals(bars: Sequence[dict], params) -> List[Signal]:
    """Detect LONG_BREAKOUT signals from bars using the given parameter set."""
    signals = []
    signal_counter = 0

    for i in range(params.lookback_bars, len(bars)):
        bar = bars[i]
        lookback_high = _compute_lookback_high(bars, i, params.lookback_bars)

        if lookback_high <= 0:
            continue

        if not is_range_high_breakout(bar, lookback_high, params.breakout_buffer_pct):
            continue

        body_pct = _compute_body_pct(bar)
        if body_pct < params.min_body_pct:
            continue

        signal_counter += 1
        signals.append(
            Signal(
                signal_id=f"sig_{signal_counter}",
                bar_index=i,
                signal_type=SignalType.LONG_BREAKOUT,
                entry_price=bar["close"],
                timestamp=bar.get("timestamp"),
                lookback_high=lookback_high,
                body_pct=body_pct,
            )
        )

    return signals


def apply_cooldown(signals: Sequence[Signal], cooldown_bars: int) -> List[Signal]:
    """Filter signals to enforce minimum gap between consecutive signals."""
    if cooldown_bars <= 0:
        return list(signals)
    if not signals:
        return []

    filtered = [signals[0]]
    for sig in signals[1:]:
        if sig.bar_index - filtered[-1].bar_index >= cooldown_bars:
            filtered.append(sig)

    return filtered
