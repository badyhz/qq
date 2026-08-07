from __future__ import annotations

import pytest

from core.paper_trading.aicoin_indicator_ports import (
    AcceleratorReferenceConfig,
    BottomTreasureConfig,
    evaluate_bottom_treasure_trigger,
    evaluate_iron_top,
)
from core.paper_trading.data_source import MarketBar


def _bar(
    index: int,
    *,
    open_: float = 100.0,
    high: float = 101.0,
    low: float = 99.0,
    close: float = 100.0,
    volume: float = 1000.0,
) -> MarketBar:
    return MarketBar(
        timestamp=float(index * 900),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        symbol="BTCUSDT",
        timeframe="15m",
    )


def test_bottom_treasure_requires_all_three_confirmations():
    bars = [_bar(i, low=95.0, close=100.0) for i in range(30)]
    # Previous bar low is 95. Current bar makes a fresh 30-bar low, then closes
    # back above that previous low.
    bars.append(_bar(30, low=90.0, close=96.0))

    result = evaluate_bottom_treasure_trigger(bars, treasure_value=10.1)

    assert result.triggered is True
    assert result.new_low is True
    assert result.treasure_above_threshold is True
    assert result.close_reclaimed_previous_low is True


def test_bottom_treasure_threshold_is_strictly_above_default_10():
    bars = [_bar(i, low=95.0, close=100.0) for i in range(30)]
    bars.append(_bar(30, low=90.0, close=96.0))

    result = evaluate_bottom_treasure_trigger(bars, treasure_value=10.0)

    assert result.triggered is False
    assert result.treasure_above_threshold is False


def test_bottom_treasure_reclaim_is_required():
    bars = [_bar(i, low=95.0, close=100.0) for i in range(30)]
    bars.append(_bar(30, low=90.0, close=94.0))

    result = evaluate_bottom_treasure_trigger(bars, treasure_value=20.0)

    assert result.new_low is True
    assert result.treasure_above_threshold is True
    assert result.close_reclaimed_previous_low is False
    assert result.triggered is False


def test_bottom_treasure_requires_enough_history():
    with pytest.raises(ValueError, match="at least 31 bars"):
        evaluate_bottom_treasure_trigger(
            [_bar(i) for i in range(30)],
            treasure_value=20.0,
        )


def test_accelerator_reference_contract_keeps_confirmed_weights_and_levels():
    cfg = AcceleratorReferenceConfig()
    cfg.validate()

    assert cfg.base_len == 21
    assert (cfg.fast_len, cfg.mid_len, cfg.slow_len) == (2, 3, 5)
    assert (cfg.start_level, cfg.extreme_level, cfg.max_level) == (15.0, 80.0, 125.0)
    assert cfg.speed_weight == pytest.approx(0.48)
    assert cfg.volatility_weight == pytest.approx(0.32)
    assert cfg.volume_weight == pytest.approx(0.20)


def test_accelerator_reference_rejects_invalid_weight_sum():
    cfg = AcceleratorReferenceConfig(speed_weight=0.50)
    with pytest.raises(ValueError, match="weights must sum to 1"):
        cfg.validate()


def _flat_iron_top_history(count: int = 61) -> list[MarketBar]:
    return [_bar(i, high=101.0, low=99.0, close=100.0) for i in range(count)]


def test_iron_top_strong_signal_requires_55_high_extreme_speed_and_weak_close():
    bars = _flat_iron_top_history()
    bars[-1] = _bar(60, open_=100.0, high=130.0, low=97.0, close=98.0)

    result = evaluate_iron_top(bars)

    assert result.new_high_30 is True
    assert result.new_high_55 is True
    assert result.new_high_30_only is False
    assert result.speed_extreme is True
    assert result.weak_close is True
    assert result.strength == 2


def test_iron_top_30_only_is_early_strength_one():
    bars = _flat_iron_top_history()
    # This high remains inside the previous 55-bar window but outside the
    # previous 30-bar window, so the latest bar can make a 30-only new high.
    bars[20] = _bar(20, high=150.0, low=99.0, close=100.0)
    bars[-1] = _bar(60, open_=100.0, high=140.0, low=97.0, close=98.0)

    result = evaluate_iron_top(bars)

    assert result.new_high_30 is True
    assert result.new_high_55 is False
    assert result.new_high_30_only is True
    assert result.speed_extreme is True
    assert result.weak_close is True
    assert result.strength == 1


def test_iron_top_does_not_fire_without_weak_close():
    bars = _flat_iron_top_history()
    bars[-1] = _bar(60, open_=100.0, high=130.0, low=99.0, close=100.0)

    result = evaluate_iron_top(bars)

    assert result.new_high_55 is True
    assert result.speed_extreme is True
    assert result.weak_close is False
    assert result.strength == 0


def test_iron_top_baseline_excludes_current_speed_value():
    bars = _flat_iron_top_history()
    bars[-1] = _bar(60, open_=100.0, high=130.0, low=97.0, close=98.0)

    result = evaluate_iron_top(bars)

    # Prior SPEED_5 values are all exactly +1%, so ref(ma(...),1) remains 1
    # and ref(sd(...),1) remains zero even though the current speed is extreme.
    assert result.speed_avg == pytest.approx(1.0)
    assert result.speed_sd == pytest.approx(0.0)
    assert result.speed_5 == pytest.approx(30.0)


def test_iron_top_requires_minimum_history_for_prior_55_speed_baseline():
    with pytest.raises(ValueError, match="at least 61 bars"):
        evaluate_iron_top(_flat_iron_top_history(60))
