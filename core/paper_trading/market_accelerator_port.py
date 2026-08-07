"""Recovered Python port of the accepted 疾速500 original-structure replica.

This is the mathematical line-generation layer recovered from the August 2026
AiCoin work.  It is intentionally pure: no network, persistence, accounts or
orders.

Recovered formula contract:

PREV_CLOSE      = ref(close, 1)
PRICE_CHANGE    = close - PREV_CLOSE
PRICE_RETURN    = PRICE_CHANGE / max(abs(PREV_CLOSE), EPS)
ABS_RETURN      = abs(PRICE_RETURN)
FAST_RETURN     = ema(PRICE_RETURN, FAST_LEN)
TREND_RETURN    = ema(PRICE_RETURN, TREND_LEN)
DIRECTION_RETURN= 0.70 * FAST_RETURN + 0.30 * TREND_RETURN
NORMAL_RETURN   = max(ema(ABS_RETURN, BASE_LEN), EPS)
NORMALIZED_SPEED= DIRECTION_RETURN / NORMAL_RETURN

TRUE_RANGE      = max(high-low, abs(high-PREV_CLOSE), abs(low-PREV_CLOSE))
SHORT_RANGE     = ema(TRUE_RANGE, FAST_LEN)
NORMAL_RANGE    = max(ema(TRUE_RANGE, BASE_LEN), EPS)
RANGE_RATIO     = min(SHORT_RANGE / NORMAL_RANGE, 2.50)

SHORT_VOLUME    = ema(volume, FAST_LEN)
NORMAL_VOLUME   = max(ema(volume, BASE_LEN), EPS)
VOLUME_RATIO    = min(SHORT_VOLUME / NORMAL_VOLUME, 2.50)

ACTIVITY        = 0.55 + 0.30 * RANGE_RATIO + 0.15 * VOLUME_RATIO
SIGNED_RAW      = NORMALIZED_SPEED * ACTIVITY * SCALE
SIGNED_SPEED    = clamp(SIGNED_RAW, -MAX_LEVEL, MAX_LEVEL)
ABS_SPEED       = abs(SIGNED_SPEED)
SLOW_SPEED      = min(ema(ABS_SPEED, SLOW_LEN) * 0.65, MAX_LEVEL)

The three plotted series are therefore:
- cyan/activity line: ABS_SPEED
- blue/directional line: SIGNED_SPEED
- red/slow line: SLOW_SPEED

The visual indicator's line formulas are kept separate from trading-regime
classification.  The strategy layer may map these lines into START/FAST/
EXTREME/DECELERATING using explicitly versioned thresholds, but such mapping is
not part of the recovered plotting formula itself.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional, Sequence

from core.paper_trading.data_source import MarketBar


@dataclass(frozen=True)
class MarketAcceleratorConfig:
    base_len: int = 21
    fast_len: int = 2
    trend_len: int = 4
    slow_len: int = 5
    scale: float = 42.0
    max_level: float = 125.0
    active_level: float = 20.0
    range_ratio_cap: float = 2.50
    volume_ratio_cap: float = 2.50
    epsilon: float = 0.000001
    fast_direction_weight: float = 0.70
    trend_direction_weight: float = 0.30
    base_activity_weight: float = 0.55
    range_activity_weight: float = 0.30
    volume_activity_weight: float = 0.15
    slow_multiplier: float = 0.65

    def validate(self) -> None:
        for name in ("base_len", "fast_len", "trend_len", "slow_len"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.scale <= 0 or self.max_level <= 0 or self.active_level < 0:
            raise ValueError("scale/max_level must be positive and active_level non-negative")
        if self.active_level > self.max_level:
            raise ValueError("active_level cannot exceed max_level")
        if self.range_ratio_cap <= 0 or self.volume_ratio_cap <= 0:
            raise ValueError("ratio caps must be positive")
        if self.epsilon <= 0:
            raise ValueError("epsilon must be positive")
        if not math.isclose(
            self.fast_direction_weight + self.trend_direction_weight,
            1.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError("direction weights must sum to 1")
        if not math.isclose(
            self.base_activity_weight
            + self.range_activity_weight
            + self.volume_activity_weight,
            1.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError("activity weights must sum to 1")
        if self.slow_multiplier <= 0:
            raise ValueError("slow_multiplier must be positive")


@dataclass(frozen=True)
class MarketAcceleratorPoint:
    index: int
    price_return: float
    fast_return: Optional[float]
    trend_return: Optional[float]
    normal_return: Optional[float]
    normalized_speed: Optional[float]
    true_range: float
    short_range: Optional[float]
    normal_range: Optional[float]
    range_ratio: Optional[float]
    short_volume: Optional[float]
    normal_volume: Optional[float]
    volume_ratio: Optional[float]
    activity: Optional[float]
    signed_speed: Optional[float]
    abs_speed: Optional[float]
    slow_speed: Optional[float]


@dataclass(frozen=True)
class MarketAcceleratorSeries:
    points: tuple[MarketAcceleratorPoint, ...]
    config: MarketAcceleratorConfig

    @property
    def latest(self) -> MarketAcceleratorPoint:
        if not self.points:
            raise ValueError("accelerator series is empty")
        return self.points[-1]


def _ema(values: Sequence[float], period: int) -> list[Optional[float]]:
    """EMA with SMA seed; None until the seed bar is available."""
    if period <= 0:
        raise ValueError("period must be positive")
    n = len(values)
    if n < period:
        return [None] * n
    result: list[Optional[float]] = [None] * (period - 1)
    seed = sum(float(v) for v in values[:period]) / period
    result.append(seed)
    alpha = 2.0 / (period + 1.0)
    previous = seed
    for value in values[period:]:
        previous = float(value) * alpha + previous * (1.0 - alpha)
        result.append(previous)
    return result


def _finite(value: float, label: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{label} must be finite")
    return value


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def calculate_market_accelerator(
    bars: Sequence[MarketBar],
    config: MarketAcceleratorConfig | None = None,
) -> MarketAcceleratorSeries:
    """Calculate the recovered 疾速500 line series for completed bars."""
    cfg = config or MarketAcceleratorConfig()
    cfg.validate()
    if not bars:
        return MarketAcceleratorSeries(points=(), config=cfg)

    closes = [_finite(bar.close, "close") for bar in bars]
    highs = [_finite(bar.high, "high") for bar in bars]
    lows = [_finite(bar.low, "low") for bar in bars]
    volumes = [_finite(bar.volume, "volume") for bar in bars]
    if any(v < 0 for v in volumes):
        raise ValueError("volume must be non-negative")

    price_returns: list[float] = []
    true_ranges: list[float] = []
    for index, (close, high, low) in enumerate(zip(closes, highs, lows)):
        if high < low:
            raise ValueError("high must be >= low")
        prev_close = closes[index - 1] if index > 0 else close
        denom = max(abs(prev_close), cfg.epsilon)
        price_returns.append((close - prev_close) / denom)
        true_ranges.append(
            max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close),
            )
        )

    abs_returns = [abs(value) for value in price_returns]
    fast_returns = _ema(price_returns, cfg.fast_len)
    trend_returns = _ema(price_returns, cfg.trend_len)
    normal_returns = _ema(abs_returns, cfg.base_len)
    short_ranges = _ema(true_ranges, cfg.fast_len)
    normal_ranges = _ema(true_ranges, cfg.base_len)
    short_volumes = _ema(volumes, cfg.fast_len)
    normal_volumes = _ema(volumes, cfg.base_len)

    signed_values: list[Optional[float]] = [None] * len(bars)
    abs_values: list[float] = [0.0] * len(bars)
    interim: list[dict[str, Optional[float]]] = []

    for index in range(len(bars)):
        fast_return = fast_returns[index]
        trend_return = trend_returns[index]
        normal_return_raw = normal_returns[index]
        short_range = short_ranges[index]
        normal_range_raw = normal_ranges[index]
        short_volume = short_volumes[index]
        normal_volume_raw = normal_volumes[index]

        if None in (
            fast_return,
            trend_return,
            normal_return_raw,
            short_range,
            normal_range_raw,
            short_volume,
            normal_volume_raw,
        ):
            interim.append({
                "normal_return": None,
                "normalized_speed": None,
                "normal_range": None,
                "range_ratio": None,
                "normal_volume": None,
                "volume_ratio": None,
                "activity": None,
            })
            continue

        assert fast_return is not None
        assert trend_return is not None
        assert normal_return_raw is not None
        assert short_range is not None
        assert normal_range_raw is not None
        assert short_volume is not None
        assert normal_volume_raw is not None

        direction_return = (
            cfg.fast_direction_weight * fast_return
            + cfg.trend_direction_weight * trend_return
        )
        normal_return = max(normal_return_raw, cfg.epsilon)
        normalized_speed = direction_return / normal_return

        normal_range = max(normal_range_raw, cfg.epsilon)
        range_ratio = min(short_range / normal_range, cfg.range_ratio_cap)

        normal_volume = max(normal_volume_raw, cfg.epsilon)
        volume_ratio = min(short_volume / normal_volume, cfg.volume_ratio_cap)

        activity = (
            cfg.base_activity_weight
            + cfg.range_activity_weight * range_ratio
            + cfg.volume_activity_weight * volume_ratio
        )
        signed_raw = normalized_speed * activity * cfg.scale
        signed_speed = _clamp(signed_raw, -cfg.max_level, cfg.max_level)
        abs_speed = abs(signed_speed)

        signed_values[index] = signed_speed
        abs_values[index] = abs_speed
        interim.append({
            "normal_return": normal_return,
            "normalized_speed": normalized_speed,
            "normal_range": normal_range,
            "range_ratio": range_ratio,
            "normal_volume": normal_volume,
            "volume_ratio": volume_ratio,
            "activity": activity,
        })

    # The slow line is EMA(abs speed, SLOW_LEN) * 0.65 capped at MAX_LEVEL.
    # Pre-warm bars with unavailable ABS_SPEED remain zero exactly because no
    # signed line exists yet; published points still expose slow_speed=None
    # until all upstream components are available and the slow EMA has seeded.
    slow_raw_series = _ema(abs_values, cfg.slow_len)

    points: list[MarketAcceleratorPoint] = []
    for index in range(len(bars)):
        signed_speed = signed_values[index]
        abs_speed = abs(signed_speed) if signed_speed is not None else None
        slow_raw = slow_raw_series[index]
        slow_speed = None
        if signed_speed is not None and slow_raw is not None:
            slow_speed = min(slow_raw * cfg.slow_multiplier, cfg.max_level)

        data = interim[index]
        points.append(MarketAcceleratorPoint(
            index=index,
            price_return=round(price_returns[index], 12),
            fast_return=(None if fast_returns[index] is None else round(fast_returns[index], 12)),
            trend_return=(None if trend_returns[index] is None else round(trend_returns[index], 12)),
            normal_return=(None if data["normal_return"] is None else round(float(data["normal_return"]), 12)),
            normalized_speed=(None if data["normalized_speed"] is None else round(float(data["normalized_speed"]), 12)),
            true_range=round(true_ranges[index], 12),
            short_range=(None if short_ranges[index] is None else round(short_ranges[index], 12)),
            normal_range=(None if data["normal_range"] is None else round(float(data["normal_range"]), 12)),
            range_ratio=(None if data["range_ratio"] is None else round(float(data["range_ratio"]), 12)),
            short_volume=(None if short_volumes[index] is None else round(short_volumes[index], 12)),
            normal_volume=(None if data["normal_volume"] is None else round(float(data["normal_volume"]), 12)),
            volume_ratio=(None if data["volume_ratio"] is None else round(float(data["volume_ratio"]), 12)),
            activity=(None if data["activity"] is None else round(float(data["activity"]), 12)),
            signed_speed=(None if signed_speed is None else round(signed_speed, 12)),
            abs_speed=(None if abs_speed is None else round(abs_speed, 12)),
            slow_speed=(None if slow_speed is None else round(slow_speed, 12)),
        ))

    return MarketAcceleratorSeries(points=tuple(points), config=cfg)
