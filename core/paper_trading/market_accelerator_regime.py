"""Versioned trading-regime mapping for recovered 疾速500 line outputs.

The recovered indicator formula is kept in ``market_accelerator_port.py``.
This module intentionally treats the mapping from plotted values to trading
states as a strategy policy, not as part of the original indicator formula.
That separation lets historical backtests tune policy thresholds without
silently changing the indicator itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from core.paper_trading.indicator_composite_strategy import AccelerationRegime
from core.paper_trading.market_accelerator_port import MarketAcceleratorPoint


@dataclass(frozen=True)
class AcceleratorRegimeConfig:
    """V1 policy thresholds for converting speed lines into trading regimes."""

    start_level: float = 20.0
    fast_level: float = 40.0
    extreme_level: float = 80.0
    deceleration_ratio: float = 0.85

    def validate(self) -> None:
        if not 0 <= self.start_level < self.fast_level < self.extreme_level:
            raise ValueError("thresholds must satisfy 0 <= start < fast < extreme")
        if not 0 < self.deceleration_ratio < 1:
            raise ValueError("deceleration_ratio must be between 0 and 1")


@dataclass(frozen=True)
class AcceleratorRegimePoint:
    index: int
    regime: AccelerationRegime
    abs_speed: Optional[float]
    signed_speed: Optional[float]
    slow_speed: Optional[float]
    reason: str


def classify_accelerator_point(
    point: MarketAcceleratorPoint,
    previous: MarketAcceleratorPoint | None = None,
    config: AcceleratorRegimeConfig | None = None,
) -> AcceleratorRegimePoint:
    """Classify one recovered indicator point into the V1 strategy regime.

    Policy order is deliberate:
    1. unavailable/pre-warm -> IDLE;
    2. extreme absolute movement -> EXTREME / no chase;
    3. deceleration after prior activity -> DECELERATING;
    4. high active speed -> FAST;
    5. active speed -> START;
    6. otherwise IDLE.

    Direction is not encoded in the regime because V1 is long-only and the
    higher-timeframe filter plus Bottom Treasure supply the long setup.  The
    signed line remains available to future policy variants.
    """
    cfg = config or AcceleratorRegimeConfig()
    cfg.validate()

    if point.abs_speed is None or point.signed_speed is None:
        return AcceleratorRegimePoint(
            index=point.index,
            regime=AccelerationRegime.IDLE,
            abs_speed=point.abs_speed,
            signed_speed=point.signed_speed,
            slow_speed=point.slow_speed,
            reason="PREWARM_OR_UNAVAILABLE",
        )

    speed = float(point.abs_speed)
    if speed >= cfg.extreme_level:
        return AcceleratorRegimePoint(
            point.index, AccelerationRegime.EXTREME,
            point.abs_speed, point.signed_speed, point.slow_speed,
            "ABS_SPEED_EXTREME",
        )

    if previous is not None and previous.abs_speed is not None:
        prev_speed = float(previous.abs_speed)
        if (
            prev_speed >= cfg.start_level
            and speed < prev_speed * cfg.deceleration_ratio
        ):
            return AcceleratorRegimePoint(
                point.index, AccelerationRegime.DECELERATING,
                point.abs_speed, point.signed_speed, point.slow_speed,
                "ABS_SPEED_DECELERATING",
            )

    if speed >= cfg.fast_level:
        regime = AccelerationRegime.FAST
        reason = "ABS_SPEED_FAST"
    elif speed >= cfg.start_level:
        regime = AccelerationRegime.START
        reason = "ABS_SPEED_ACTIVE"
    else:
        regime = AccelerationRegime.IDLE
        reason = "ABS_SPEED_BELOW_ACTIVE"

    return AcceleratorRegimePoint(
        point.index,
        regime,
        point.abs_speed,
        point.signed_speed,
        point.slow_speed,
        reason,
    )


def classify_accelerator_series(
    points: Sequence[MarketAcceleratorPoint],
    config: AcceleratorRegimeConfig | None = None,
) -> tuple[AcceleratorRegimePoint, ...]:
    """Classify an entire speed series without future leakage."""
    cfg = config or AcceleratorRegimeConfig()
    cfg.validate()
    output: list[AcceleratorRegimePoint] = []
    previous: MarketAcceleratorPoint | None = None
    for point in points:
        output.append(classify_accelerator_point(point, previous, cfg))
        previous = point
    return tuple(output)
