from __future__ import annotations

import pytest

from core.paper_trading.data_source import MarketBar
from core.paper_trading.market_accelerator_port import (
    MarketAcceleratorConfig,
    calculate_market_accelerator,
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

    result = calculate_market_accelerator(bars)
    latest = result.latest

    assert latest.normalized_speed == pytest.approx(0.0)
    assert latest.signed_speed == pytest.approx(0.0)
    assert latest.abs_speed == pytest.approx(0.0)
    assert latest.range_ratio == pytest.approx(1.0)
    assert latest.volume_ratio == pytest.approx(1.0)
    assert latest.activity == pytest.approx(1.0)


def test_activity_formula_uses_055_030_015_weights():
    bars = [_bar(i) for i in range(40)]
    result = calculate_market_accelerator(bars)
    latest = result.latest

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
        bars.append(_bar(i, close=200.0 + (i - 35) * 25.0,
                         high=205.0 + (i - 35) * 25.0,
                         low=195.0 + (i - 35) * 25.0,
                         volume=5000.0))

    latest = calculate_market_accelerator(bars).latest

    assert latest.slow_speed is not None
    assert 0.0 <= latest.slow_speed <= 125.0
    # Formula invariant: the published slow line can never exceed 65% of a
    # fully saturated steady-state ABS_SPEED before MAX_LEVEL capping.
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
