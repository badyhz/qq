from __future__ import annotations

from core.paper_trading.indicator_composite_strategy import AccelerationRegime
from core.paper_trading.market_accelerator_port import MarketAcceleratorPoint
from core.paper_trading.market_accelerator_regime import (
    AcceleratorRegimeConfig,
    classify_accelerator_point,
    classify_accelerator_series,
)


def _point(index: int, speed: float | None) -> MarketAcceleratorPoint:
    signed = speed
    return MarketAcceleratorPoint(
        index=index,
        price_return=0.0,
        fast_return=0.0 if speed is not None else None,
        trend_return=0.0 if speed is not None else None,
        normal_return=1.0 if speed is not None else None,
        normalized_speed=0.0 if speed is not None else None,
        true_range=1.0,
        short_range=1.0 if speed is not None else None,
        normal_range=1.0 if speed is not None else None,
        range_ratio=1.0 if speed is not None else None,
        short_volume=1.0 if speed is not None else None,
        normal_volume=1.0 if speed is not None else None,
        volume_ratio=1.0 if speed is not None else None,
        activity=1.0 if speed is not None else None,
        signed_speed=signed,
        abs_speed=(abs(speed) if speed is not None else None),
        slow_speed=(abs(speed) * 0.65 if speed is not None else None),
    )


def test_default_v1_policy_thresholds():
    cfg = AcceleratorRegimeConfig()
    cfg.validate()
    assert cfg.start_level == 20.0
    assert cfg.fast_level == 40.0
    assert cfg.extreme_level == 80.0
    assert cfg.deceleration_ratio == 0.85


def test_pre_warm_is_idle():
    result = classify_accelerator_point(_point(0, None))
    assert result.regime == AccelerationRegime.IDLE


def test_below_active_is_idle():
    result = classify_accelerator_point(_point(1, 19.9))
    assert result.regime == AccelerationRegime.IDLE


def test_active_is_start():
    result = classify_accelerator_point(_point(1, 20.0))
    assert result.regime == AccelerationRegime.START


def test_fast_threshold_is_fast():
    result = classify_accelerator_point(_point(1, 40.0))
    assert result.regime == AccelerationRegime.FAST


def test_extreme_threshold_is_no_chase_extreme():
    result = classify_accelerator_point(_point(1, 80.0))
    assert result.regime == AccelerationRegime.EXTREME


def test_deceleration_has_priority_over_start_or_fast():
    previous = _point(0, 60.0)
    current = _point(1, 45.0)  # < 60 * 0.85 = 51
    result = classify_accelerator_point(current, previous)
    assert result.regime == AccelerationRegime.DECELERATING


def test_extreme_has_priority_over_deceleration():
    previous = _point(0, 125.0)
    current = _point(1, 80.0)
    result = classify_accelerator_point(current, previous)
    assert result.regime == AccelerationRegime.EXTREME


def test_series_classification_uses_only_previous_point():
    points = [_point(0, 10.0), _point(1, 50.0), _point(2, 30.0)]
    regimes = classify_accelerator_series(points)
    assert [item.regime for item in regimes] == [
        AccelerationRegime.IDLE,
        AccelerationRegime.FAST,
        AccelerationRegime.DECELERATING,
    ]
