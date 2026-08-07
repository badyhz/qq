"""Recovered early complete Bottom Treasure formula for research comparison.

This is NOT silently substituted for the later SMMA-based AiCoin variant.  It
is preserved as an explicitly-versioned research formula because the full early
formula was recoverable from the August 2026 conversation and can therefore be
backtested without guessing.

Recovered formula:

N = 30
K = 618
S = 3
M = 5  # retained historical parameter; unused in the recovered expression
LOW_CHANGE = LOW - REF(LOW, 1)
DOWN_PRESSURE = ABS(MIN(LOW_CHANGE, 0))
UP_REBOUND = MAX(LOW_CHANGE, 0)
PRESSURE_RATIO = DOWN_PRESSURE / (UP_REBOUND + 0.01)
RAW_PRESSURE = EMA(PRESSURE_RATIO, S)
TREASURE_RAW = RAW_PRESSURE / K * 100
TREASURE = MIN(TREASURE_RAW, 100)
NEW_LOW = LOW <= LLV(LOW, N)
BUY_SIGNAL = NEW_LOW AND TREASURE > 10 AND CLOSE > REF(LOW, 1)
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from core.paper_trading.data_source import MarketBar


FORMULA_VERSION = "bottom_treasure_recovered_v0"


@dataclass(frozen=True)
class RecoveredBottomTreasureConfig:
    lookback: int = 30
    scale_k: float = 618.0
    pressure_ema_len: int = 3
    historical_m: int = 5
    denominator_offset: float = 0.01
    buy_threshold: float = 10.0
    max_treasure: float = 100.0

    def validate(self) -> None:
        if self.lookback <= 0 or self.pressure_ema_len <= 0:
            raise ValueError("lookback and pressure_ema_len must be positive")
        if self.scale_k <= 0 or self.denominator_offset <= 0:
            raise ValueError("scale_k and denominator_offset must be positive")
        if self.max_treasure <= 0:
            raise ValueError("max_treasure must be positive")
        if not math.isfinite(self.buy_threshold):
            raise ValueError("buy_threshold must be finite")


@dataclass(frozen=True)
class RecoveredBottomTreasurePoint:
    index: int
    low_change: float
    down_pressure: float
    up_rebound: float
    pressure_ratio: float
    raw_pressure: float
    treasure: float
    new_low: bool
    close_reclaimed_previous_low: bool
    buy_signal: bool
    formula_version: str = FORMULA_VERSION


def _streaming_ema(values: Sequence[float], period: int) -> list[float]:
    """Streaming EMA seeded by the first value, matching formula-style usage."""
    if period <= 0:
        raise ValueError("period must be positive")
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    result = [float(values[0])]
    previous = result[0]
    for value in values[1:]:
        previous = float(value) * alpha + previous * (1.0 - alpha)
        result.append(previous)
    return result


def calculate_recovered_bottom_treasure(
    bars: Sequence[MarketBar],
    config: RecoveredBottomTreasureConfig | None = None,
) -> tuple[RecoveredBottomTreasurePoint, ...]:
    """Calculate the complete recovered-v0 formula without future leakage."""
    cfg = config or RecoveredBottomTreasureConfig()
    cfg.validate()
    if not bars:
        return ()

    lows = [float(bar.low) for bar in bars]
    closes = [float(bar.close) for bar in bars]
    if any(not math.isfinite(value) or value <= 0 for value in lows + closes):
        raise ValueError("low/close values must be finite and positive")

    low_changes: list[float] = []
    down_pressures: list[float] = []
    up_rebounds: list[float] = []
    pressure_ratios: list[float] = []

    for index, low in enumerate(lows):
        previous_low = lows[index - 1] if index > 0 else low
        low_change = low - previous_low
        down_pressure = abs(min(low_change, 0.0))
        up_rebound = max(low_change, 0.0)
        pressure_ratio = down_pressure / (up_rebound + cfg.denominator_offset)
        low_changes.append(low_change)
        down_pressures.append(down_pressure)
        up_rebounds.append(up_rebound)
        pressure_ratios.append(pressure_ratio)

    raw_pressures = _streaming_ema(pressure_ratios, cfg.pressure_ema_len)
    output: list[RecoveredBottomTreasurePoint] = []

    for index in range(len(bars)):
        raw_pressure = raw_pressures[index]
        treasure = min(raw_pressure / cfg.scale_k * 100.0, cfg.max_treasure)
        window_start = max(0, index - cfg.lookback + 1)
        window_low = min(lows[window_start:index + 1])
        new_low = lows[index] <= window_low
        reclaimed = index > 0 and closes[index] > lows[index - 1]
        buy_signal = (
            index > 0
            and new_low
            and treasure > cfg.buy_threshold
            and reclaimed
        )
        output.append(RecoveredBottomTreasurePoint(
            index=index,
            low_change=round(low_changes[index], 12),
            down_pressure=round(down_pressures[index], 12),
            up_rebound=round(up_rebounds[index], 12),
            pressure_ratio=round(pressure_ratios[index], 12),
            raw_pressure=round(raw_pressure, 12),
            treasure=round(treasure, 12),
            new_low=new_low,
            close_reclaimed_previous_low=reclaimed,
            buy_signal=buy_signal,
        ))

    return tuple(output)
