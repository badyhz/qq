from __future__ import annotations

import pytest

from core.paper_trading.bottom_treasure_recovered_v0 import (
    FORMULA_VERSION,
    RecoveredBottomTreasureConfig,
    calculate_recovered_bottom_treasure,
)
from core.paper_trading.data_source import MarketBar


def _bar(index: int, *, low=100.0, close=101.0) -> MarketBar:
    return MarketBar(
        timestamp=float(index * 900),
        open=101.0,
        high=max(102.0, close),
        low=low,
        close=close,
        volume=1000.0,
        symbol="BTCUSDT",
        timeframe="15m",
    )


def test_recovered_constants_are_explicit_and_versioned():
    cfg = RecoveredBottomTreasureConfig()
    cfg.validate()
    assert cfg.lookback == 30
    assert cfg.scale_k == 618.0
    assert cfg.pressure_ema_len == 3
    assert cfg.historical_m == 5
    assert cfg.buy_threshold == 10.0
    assert FORMULA_VERSION == "bottom_treasure_recovered_v0"


def test_large_new_low_pressure_can_trigger_recovered_buy_signal():
    bars = [_bar(i) for i in range(30)]
    bars.append(_bar(30, low=90.0, close=101.0))

    points = calculate_recovered_bottom_treasure(bars)
    latest = points[-1]

    assert latest.new_low is True
    assert latest.close_reclaimed_previous_low is True
    assert latest.pressure_ratio == pytest.approx(1000.0)
    assert latest.treasure > 10.0
    assert latest.buy_signal is True
    assert latest.formula_version == FORMULA_VERSION


def test_reclaim_of_previous_low_is_required():
    bars = [_bar(i) for i in range(30)]
    bars.append(_bar(30, low=90.0, close=99.0))

    latest = calculate_recovered_bottom_treasure(bars)[-1]

    assert latest.new_low is True
    assert latest.treasure > 10.0
    assert latest.close_reclaimed_previous_low is False
    assert latest.buy_signal is False


def test_treasure_is_capped_at_100():
    bars = [_bar(i) for i in range(30)]
    bars.append(_bar(30, low=1.0, close=101.0))

    latest = calculate_recovered_bottom_treasure(bars)[-1]
    assert latest.treasure == pytest.approx(100.0)


def test_threshold_is_strictly_greater_than_10():
    cfg = RecoveredBottomTreasureConfig(buy_threshold=100.0)
    bars = [_bar(i) for i in range(30)]
    bars.append(_bar(30, low=1.0, close=101.0))

    latest = calculate_recovered_bottom_treasure(bars, cfg)[-1]
    assert latest.treasure == 100.0
    assert latest.buy_signal is False


def test_empty_input_is_empty():
    assert calculate_recovered_bottom_treasure([]) == ()


def test_invalid_price_fails_closed():
    with pytest.raises(ValueError, match="finite and positive"):
        calculate_recovered_bottom_treasure([_bar(0, low=0.0, close=1.0)])
