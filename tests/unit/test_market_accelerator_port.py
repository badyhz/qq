from __future__ import annotations

import pytest

from core.paper_trading.data_source import MarketBar
from core.paper_trading.indicator_composite_strategy import AccelerationRegime
from core.paper_trading.market_accelerator_port import (
    AcceleratorRegimeConfig,
    MarketAcceleratorConfig,
    MarketAcceleratorPoint,
    calculate_market_accelerator,
    classify_accelerator_point,
    classify_accelerator_series,
)


def _bar(
    index: int,
    *,
    close: float = 100.0,
    high: float = 101.0,
    low: float = 99.0,
    volume: float = 1000.0,
) -> MarketBar:
    return MarketBar(
        timestamp=float(index * 900),
        open=close,
        high=high,
        low=low,
        close=close,
        volume=volume,
        symbol="BTCUSDT",
        timeframe="15m",
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


def test_recovered_default_parameters_match_accepted_replica():
    cfg = MarketAcceleratorConfig()
    cfg.validate()

    assert cfg.base_len == 21
    assert cfg.fast_len == 2
    assert cfg.trend_len == 4
    assert cfg.slow_len == 5
    assert cfg.scale == 42.0
    assert cfg.max_level == 125.0
    assert cfg.active_level == 20.0
    assert cfg.range_ratio_cap == 2.50
    assert cfg.volume_ratio_cap == 2.50
    assert cfg.fast_direction_weight == pytest.approx(0.70)
    assert cfg.trend_direction_weight == pytest.approx(0.30)
    assert cfg.base_activity_weight == pytest.approx(0.55)
    assert cfg.range_activity_weight == pytest.approx(0.30)
    assert cfg.volume_activity_weight == pytest.approx(0.15)
    assert cfg.slow_multiplier == pytest.approx(0.65)


def test_flat_market_converges_to_zero_directional_speed():
    bars = [_bar(i) for i in range(40)]
    latest = calculate_market_accelerator(bars).latest

    assert latest.normalized_speed == pytest.approx(0.0)
    assert latest.signed_speed == pytest.approx(0.0)
    assert latest.abs_speed == pytest.approx(0.0)
    assert latest.range_ratio == pytest.approx(1.0)
    assert latest.volume_ratio == pytest.approx(1.0)
    assert latest.activity == pytest.approx(1.0)


def test_activity_formula_uses_055_030_015_weights():
    bars = [_bar(i) for i in range(40)]
    latest = calculate_market_accelerator(bars).latest

    expected = 0.55 + 0.30 * latest.range_ratio + 0.15 * latest.volume_ratio
    assert latest.activity == pytest.approx(expected)


def test_ratio_caps_limit_range_and_volume_bursts_to_250():
    bars = [_bar(i) for i in range(39)]
    bars.append(_bar(39, high=160.0, low=40.0, volume=1_000_000.0))

    latest = calculate_market_accelerator(bars).latest
    assert latest.range_ratio == pytest.approx(2.50)
    assert latest.volume_ratio == pytest.approx(2.50)


def test_signed_speed_is_clamped_to_positive_max_level():
    bars = [_bar(i) for i in range(39)]
    bars.append(_bar(39, close=200.0, high=201.0, low=99.0, volume=1000.0))

    latest = calculate_market_accelerator(bars).latest
    assert latest.signed_speed == pytest.approx(125.0)
    assert latest.abs_speed == pytest.approx(125.0)


def test_signed_speed_is_clamped_to_negative_max_level():
    bars = [_bar(i) for i in range(39)]
    bars.append(_bar(39, close=20.0, high=101.0, low=19.0, volume=1000.0))

    latest = calculate_market_accelerator(bars).latest
    assert latest.signed_speed == pytest.approx(-125.0)
    assert latest.abs_speed == pytest.approx(125.0)


def test_slow_line_is_ema_of_absolute_speed_times_065_and_capped():
    bars = [_bar(i) for i in range(35)]
    for i in range(35, 45):
        bars.append(_bar(
            i,
            close=200.0 + (i - 35) * 25.0,
            high=205.0 + (i - 35) * 25.0,
            low=195.0 + (i - 35) * 25.0,
            volume=5000.0,
        ))

    latest = calculate_market_accelerator(bars).latest
    assert latest.slow_speed is not None
    assert 0.0 <= latest.slow_speed <= 125.0
    assert latest.slow_speed <= 125.0 * 0.65 + 1e-9


def test_empty_input_returns_empty_series():
    result = calculate_market_accelerator([])
    assert result.points == ()
    with pytest.raises(ValueError, match="empty"):
        _ = result.latest


def test_invalid_weight_contract_is_rejected():
    cfg = MarketAcceleratorConfig(fast_direction_weight=0.80)
    with pytest.raises(ValueError, match="direction weights"):
        cfg.validate()


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
    current = _point(1, 45.0)
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
