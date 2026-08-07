"""Pure Python ports of confirmed AiCoin indicator contracts.

Only formula behavior explicitly recovered from the accepted AiCoin work is
implemented here. Missing or ambiguous parts are not guessed.

Bottom Treasure is represented in two deliberately separate contracts:

1. ``evaluate_bottom_treasure_trigger`` — the later confirmed three-condition
   trigger, with treasure value supplied externally so the unfinished final
   SMMA value formula is not guessed.
2. ``calculate_recovered_bottom_treasure`` — an earlier complete formula,
   explicitly versioned ``bottom_treasure_recovered_v0`` for research only.

Revised Iron Top / 修正版铁顶临界 is also implemented here.

Market Accelerator / 疾速500 lives in ``market_accelerator_port`` so that one
module remains the sole authority for its line formula and regime policy.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from core.paper_trading.data_source import MarketBar


BOTTOM_TREASURE_RECOVERED_VERSION = "bottom_treasure_recovered_v0"


@dataclass(frozen=True)
class BottomTreasureConfig:
    lookback: int = 30
    buy_threshold: float = 10.0

    def validate(self) -> None:
        if self.lookback <= 0:
            raise ValueError("lookback must be positive")
        if not math.isfinite(self.buy_threshold):
            raise ValueError("buy_threshold must be finite")


@dataclass(frozen=True)
class BottomTreasureResult:
    triggered: bool
    new_low: bool
    treasure_above_threshold: bool
    close_reclaimed_previous_low: bool
    treasure_value: float
    threshold: float


@dataclass(frozen=True)
class RecoveredBottomTreasureConfig:
    """Earlier complete Bottom Treasure formula retained for research only."""

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
    formula_version: str = BOTTOM_TREASURE_RECOVERED_VERSION


@dataclass(frozen=True)
class IronTopConfig:
    short_lookback: int = 30
    long_lookback: int = 55
    speed_lookback: int = 5
    speed_baseline_length: int = 55
    speed_sigma: float = 1.5

    def validate(self) -> None:
        if self.short_lookback <= 0 or self.long_lookback <= 0:
            raise ValueError("high lookbacks must be positive")
        if self.short_lookback >= self.long_lookback:
            raise ValueError("short_lookback must be less than long_lookback")
        if self.speed_lookback <= 0 or self.speed_baseline_length <= 1:
            raise ValueError("speed lookbacks are invalid")
        if self.speed_sigma <= 0:
            raise ValueError("speed_sigma must be positive")


@dataclass(frozen=True)
class IronTopResult:
    strength: int  # 0 none, 1 early 30-only, 2 strong 55-bar
    new_high_30: bool
    new_high_55: bool
    new_high_30_only: bool
    speed_5: float
    speed_avg: float
    speed_sd: float
    speed_extreme: bool
    weak_close: bool


def evaluate_bottom_treasure_trigger(
    bars: Sequence[MarketBar],
    treasure_value: float,
    config: BottomTreasureConfig | None = None,
) -> BottomTreasureResult:
    """Evaluate the confirmed later three-condition Bottom Treasure trigger."""
    cfg = config or BottomTreasureConfig()
    cfg.validate()
    if not math.isfinite(treasure_value):
        raise ValueError("treasure_value must be finite")
    if len(bars) < cfg.lookback + 1:
        raise ValueError(f"at least {cfg.lookback + 1} bars are required")

    current = bars[-1]
    previous = bars[-2]
    previous_window = bars[-(cfg.lookback + 1):-1]
    previous_low = min(float(bar.low) for bar in previous_window)

    new_low = float(current.low) < previous_low
    treasure_above = float(treasure_value) > cfg.buy_threshold
    reclaimed = float(current.close) > float(previous.low)

    return BottomTreasureResult(
        triggered=new_low and treasure_above and reclaimed,
        new_low=new_low,
        treasure_above_threshold=treasure_above,
        close_reclaimed_previous_low=reclaimed,
        treasure_value=float(treasure_value),
        threshold=float(cfg.buy_threshold),
    )


def _streaming_ema(values: Sequence[float], period: int) -> list[float]:
    """Streaming EMA seeded by the first value for recovered formula research."""
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
    """Calculate the complete recovered-v0 formula without future leakage.

    Recovered formula:

    N = 30
    K = 618
    S = 3
    M = 5  # retained historical parameter; unused in expression
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


def _speed_5_at(bars: Sequence[MarketBar], index: int, lookback: int) -> float:
    base_index = index - lookback
    if base_index < 0:
        raise ValueError("insufficient bars for speed calculation")
    base_close = float(bars[base_index].close)
    if base_close <= 0:
        raise ValueError("speed base close must be positive")
    return (float(bars[index].high) / base_close - 1.0) * 100.0


def _population_sd(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("standard deviation requires values")
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def evaluate_iron_top(
    bars: Sequence[MarketBar],
    config: IronTopConfig | None = None,
) -> IronTopResult:
    """Evaluate the confirmed revised Iron Top signal on the latest bar."""
    cfg = config or IronTopConfig()
    cfg.validate()

    current_index = len(bars) - 1
    minimum_index = cfg.speed_lookback + cfg.speed_baseline_length
    minimum_bars = max(cfg.long_lookback + 1, minimum_index + 1)
    if len(bars) < minimum_bars:
        raise ValueError(f"at least {minimum_bars} bars are required")

    current = bars[current_index]
    previous = bars[current_index - 1]

    prior_30 = bars[-(cfg.short_lookback + 1):-1]
    prior_55 = bars[-(cfg.long_lookback + 1):-1]
    previous_high_30 = max(float(bar.high) for bar in prior_30)
    previous_high_55 = max(float(bar.high) for bar in prior_55)

    new_high_30 = float(current.high) > previous_high_30
    new_high_55 = float(current.high) > previous_high_55
    new_high_30_only = new_high_30 and not new_high_55

    speed_5 = _speed_5_at(bars, current_index, cfg.speed_lookback)
    baseline_end = current_index
    baseline_start = baseline_end - cfg.speed_baseline_length
    prior_speeds = [
        _speed_5_at(bars, index, cfg.speed_lookback)
        for index in range(baseline_start, baseline_end)
    ]
    speed_avg = sum(prior_speeds) / len(prior_speeds)
    speed_sd = _population_sd(prior_speeds)
    speed_extreme = speed_5 > speed_avg + cfg.speed_sigma * speed_sd
    weak_close = float(current.close) < float(previous.low)

    strength = 0
    if speed_extreme and weak_close:
        if new_high_55:
            strength = 2
        elif new_high_30_only:
            strength = 1

    return IronTopResult(
        strength=strength,
        new_high_30=new_high_30,
        new_high_55=new_high_55,
        new_high_30_only=new_high_30_only,
        speed_5=round(speed_5, 10),
        speed_avg=round(speed_avg, 10),
        speed_sd=round(speed_sd, 10),
        speed_extreme=speed_extreme,
        weak_close=weak_close,
    )
