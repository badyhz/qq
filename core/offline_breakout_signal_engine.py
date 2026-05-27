"""Offline breakout signal engine — pure functions, no I/O.

Scans historical bars for breakout signals using configurable parameters.
No network, no live data, no side effects.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence


@dataclass(frozen=True)
class BreakoutSignalParams:
    """Parameters for breakout signal detection."""
    lookback: int = 20
    breakout_threshold: float = 0.005
    volume_multiplier: float = 1.5
    min_bars_required: int = 30
    cooldown_bars: int = 3
    stop_atr_multiplier: float = 1.5
    take_profit_rr: float = 2.0

    def __post_init__(self) -> None:
        if self.lookback <= 0:
            raise ValueError("lookback must be > 0")
        if self.breakout_threshold < 0:
            raise ValueError("breakout_threshold must be >= 0")
        if self.volume_multiplier < 0:
            raise ValueError("volume_multiplier must be >= 0")
        if self.min_bars_required <= 0:
            raise ValueError("min_bars_required must be > 0")


@dataclass(frozen=True)
class BreakoutSignal:
    """A detected breakout signal."""
    signal_id: str
    bar_index: int
    timestamp: float
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    stop_price: float
    tp_price: float
    breakout_level: float
    volume_ratio: float
    atr_value: float
    confidence_score: float


def _compute_atr(highs: List[float], lows: List[float], closes: List[float], period: int) -> float:
    """Compute ATR over the most recent `period` bars."""
    if len(highs) < period + 1:
        return 0.0
    trs = []
    for i in range(-period, 0):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    return sum(trs) / len(trs) if trs else 0.0


def _compute_rolling_high(highs: List[float], lookback: int) -> float:
    """Highest high over the last `lookback` bars (excluding current)."""
    if len(highs) < lookback + 1:
        return max(highs[:-1]) if len(highs) > 1 else 0.0
    return max(highs[-(lookback + 1):-1])


def _compute_rolling_low(lows: List[float], lookback: int) -> float:
    """Lowest low over the last `lookback` bars (excluding current)."""
    if len(lows) < lookback + 1:
        return min(lows[:-1]) if len(lows) > 1 else 0.0
    return min(lows[-(lookback + 1):-1])


def _compute_avg_volume(volumes: List[float], lookback: int) -> float:
    """Average volume over the last `lookback` bars."""
    if len(volumes) < lookback:
        return sum(volumes) / len(volumes) if volumes else 0.0
    return sum(volumes[-lookback:]) / lookback


def scan_breakout_signals(
    bars: Sequence[dict],
    params: BreakoutSignalParams | None = None,
) -> List[BreakoutSignal]:
    """Scan bar data for breakout signals.

    Parameters
    ----------
    bars : Sequence[dict]
        Bar dicts with at minimum: timestamp, open, high, low, close, volume.
    params : BreakoutSignalParams, optional

    Returns
    -------
    List[BreakoutSignal]
        Detected signals in chronological order.
    """
    if params is None:
        params = BreakoutSignalParams()

    n = len(bars)
    if n < params.min_bars_required:
        return []

    signals: List[BreakoutSignal] = []
    cooldown_remaining = 0

    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]
    closes = [float(b["close"]) for b in bars]
    volumes = [float(b["volume"]) for b in bars]

    for i in range(params.lookback + 1, n):
        if cooldown_remaining > 0:
            cooldown_remaining -= 1
            continue

        rolling_high = _compute_rolling_high(highs[:i + 1], params.lookback)
        rolling_low = _compute_rolling_low(lows[:i + 1], params.lookback)
        atr_val = _compute_atr(highs[:i + 1], lows[:i + 1], closes[:i + 1], params.lookback)
        avg_vol = _compute_avg_volume(volumes[:i + 1], params.lookback)

        close = closes[i]
        volume = volumes[i]
        volume_ratio = volume / avg_vol if avg_vol > 0 else 0.0

        # Upside breakout
        if close > rolling_high * (1 + params.breakout_threshold):
            if volume_ratio >= params.volume_multiplier:
                stop = close - (atr_val * params.stop_atr_multiplier)
                reward = (close - stop) * params.take_profit_rr
                tp = close + reward
                confidence = min(1.0, volume_ratio / (params.volume_multiplier * 2))
                signals.append(BreakoutSignal(
                    signal_id=f"breakout_{i}",
                    bar_index=i,
                    timestamp=float(bars[i].get("timestamp", i)),
                    direction="LONG",
                    entry_price=close,
                    stop_price=round(stop, 6),
                    tp_price=round(tp, 6),
                    breakout_level=round(rolling_high, 6),
                    volume_ratio=round(volume_ratio, 6),
                    atr_value=round(atr_val, 6),
                    confidence_score=round(confidence, 6),
                ))
                cooldown_remaining = params.cooldown_bars
                continue

        # Downside breakout
        if close < rolling_low * (1 - params.breakout_threshold):
            if volume_ratio >= params.volume_multiplier:
                stop = close + (atr_val * params.stop_atr_multiplier)
                reward = (stop - close) * params.take_profit_rr
                tp = close - reward
                confidence = min(1.0, volume_ratio / (params.volume_multiplier * 2))
                signals.append(BreakoutSignal(
                    signal_id=f"breakout_{i}",
                    bar_index=i,
                    timestamp=float(bars[i].get("timestamp", i)),
                    direction="SHORT",
                    entry_price=close,
                    stop_price=round(stop, 6),
                    tp_price=round(tp, 6),
                    breakout_level=round(rolling_low, 6),
                    volume_ratio=round(volume_ratio, 6),
                    atr_value=round(atr_val, 6),
                    confidence_score=round(confidence, 6),
                ))
                cooldown_remaining = params.cooldown_bars

    return signals
