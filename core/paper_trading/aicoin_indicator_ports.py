"""Pure Python ports of confirmed AiCoin indicator contracts.

Only formula behavior that is explicitly known from the accepted AiCoin work is
implemented here. Missing or ambiguous parts are not guessed.

Confirmed contracts currently covered:

Bottom Treasure / 底部寻宝 V1 trigger
- current bar makes a new low versus the previous 30 completed bars;
- externally computed treasure value is strictly above the threshold (default 10);
- current close reclaims the previous bar's low.

Revised Iron Top / 修正版铁顶临界
- current high makes a new 30- or 55-bar high versus the prior completed window;
- SPEED_5 = (current_high / close_5_bars_ago - 1) * 100;
- SPEED_AVG = prior 55-value mean of SPEED_5;
- SPEED_SD = prior 55-value population standard deviation of SPEED_5;
- speed is extreme when SPEED_5 > SPEED_AVG + 1.5 * SPEED_SD;
- close turns weak when current close < previous bar low;
- 55-bar new high is the stronger signal; 30-only is the early signal.

Market Accelerator / 疾速500 is intentionally implemented in the dedicated
``market_accelerator_port`` module so there is only one authoritative formula
source for that indicator.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from core.paper_trading.data_source import MarketBar


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
    """Evaluate the confirmed three-condition Bottom Treasure entry trigger.

    ``treasure_value`` is passed in explicitly because the final accepted
    pressure/treasure-value formula is not fully recoverable from the current
    repository. This keeps the known trigger semantics exact without silently
    substituting a different formula.
    """
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
    """Evaluate the confirmed revised Iron Top signal on the latest bar.

    Baseline mean/SD use only prior SPEED_5 values, matching the AiCoin
    ``ref(ma(...), 1)`` / ``ref(sd(...), 1)`` contract and avoiding look-ahead.
    """
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
