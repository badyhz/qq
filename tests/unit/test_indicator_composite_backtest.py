from __future__ import annotations

import pytest

from core.indicator_composite_backtest import (
    CompositeBacktestConfig,
    run_indicator_composite_backtest,
)
from core.offline_backtest_trade_simulator import TradeSimulationParams
from core.paper_trading.data_source import MarketBar
from core.paper_trading.indicator_composite_strategy import (
    AccelerationRegime,
    HigherTimeframeTrend,
    IndicatorCompositeState,
)


def _bar(index: int, *, close=100.0, high=101.0, low=99.0) -> MarketBar:
    return MarketBar(
        timestamp=float(index * 900),
        open=close,
        high=high,
        low=low,
        close=close,
        volume=1000.0,
        symbol="BTCUSDT",
        timeframe="15m",
    )


def _state(
    *,
    trigger: bool = False,
    regime: AccelerationRegime = AccelerationRegime.START,
    trend: HigherTimeframeTrend = HigherTimeframeTrend.NEUTRAL,
) -> IndicatorCompositeState:
    return IndicatorCompositeState(
        bottom_treasure_trigger=trigger,
        acceleration_regime=regime,
        higher_timeframe_trend=trend,
        iron_top_strength=0,
        atr=2.0,
    )


def test_backtest_reuses_existing_simulator_for_take_profit_trade():
    bars = [
        _bar(0, close=100.0, high=101.0, low=98.0),
        _bar(1, close=104.0, high=106.0, low=100.0),
        _bar(2, close=104.0, high=105.0, low=103.0),
    ]
    states = [_state(trigger=True), _state(), _state()]
    cfg = CompositeBacktestConfig(
        simulation=TradeSimulationParams(
            slippage_pct=0.0,
            fee_pct=0.0,
            max_hold_bars=10,
        )
    )

    result = run_indicator_composite_backtest(bars, states, cfg)

    assert result["signal_count"] == 1
    assert result["trade_count"] == 1
    assert result["blocked_risk_gate"] == 0
    assert result["signals"][0]["risk_gate_status"] == "PASS"
    assert result["trades"][0]["exit_reason"] == "TAKE_PROFIT"
    assert result["trades"][0]["realized_r"] == pytest.approx(2.0)
    assert result["dynamic_exit_overlay_applied"] is False
    assert result["orders_enabled"] is False


def test_extreme_regime_filters_bottom_signal_before_trade_creation():
    bars = [_bar(0), _bar(1)]
    states = [
        _state(trigger=True, regime=AccelerationRegime.EXTREME),
        _state(),
    ]

    result = run_indicator_composite_backtest(bars, states)

    assert result["signal_count"] == 0
    assert result["trade_count"] == 0


def test_higher_timeframe_downtrend_filters_entry():
    bars = [_bar(0), _bar(1)]
    states = [
        _state(trigger=True, trend=HigherTimeframeTrend.DOWN),
        _state(),
    ]

    result = run_indicator_composite_backtest(bars, states)

    assert result["signal_count"] == 0
    assert result["trade_count"] == 0


def test_shadow_risk_gate_blocks_wide_stop_signal():
    bars = [
        _bar(0, close=100.0, high=101.0, low=80.0),
        _bar(1, close=110.0, high=120.0, low=90.0),
    ]
    states = [_state(trigger=True), _state()]

    result = run_indicator_composite_backtest(bars, states)

    assert result["signal_count"] == 1
    assert result["trade_count"] == 0
    assert result["blocked_risk_gate"] == 1
    assert result["signals"][0]["risk_gate_status"] == "BLOCK"
    assert any(
        "risk_distance_pct" in reason
        for reason in result["signals"][0]["risk_gate_reasons"]
    )


def test_backtest_max_risk_above_shadow_limit_is_blocked_by_same_gate():
    bars = [
        _bar(0, close=100.0, high=101.0, low=98.0),
        _bar(1, close=104.0, high=106.0, low=100.0),
    ]
    states = [_state(trigger=True), _state()]
    cfg = CompositeBacktestConfig(max_risk_pct=1.0)

    result = run_indicator_composite_backtest(bars, states, cfg)

    assert result["signal_count"] == 1
    assert result["trade_count"] == 0
    assert result["blocked_risk_gate"] == 1
    assert any(
        "max_risk_pct" in reason
        for reason in result["signals"][0]["risk_gate_reasons"]
    )


def test_overlapping_signal_is_counted_but_not_opened_twice():
    bars = [
        _bar(0, close=100.0, high=101.0, low=98.0),
        _bar(1, close=100.5, high=101.0, low=99.5),
        _bar(2, close=104.0, high=106.0, low=100.0),
        _bar(3, close=104.0, high=105.0, low=103.0),
    ]
    states = [
        _state(trigger=True),
        _state(trigger=True),
        _state(),
        _state(),
    ]
    cfg = CompositeBacktestConfig(
        simulation=TradeSimulationParams(
            slippage_pct=0.0,
            fee_pct=0.0,
            max_hold_bars=10,
        )
    )

    result = run_indicator_composite_backtest(bars, states, cfg)

    assert result["signal_count"] == 2
    assert result["trade_count"] == 1
    assert result["blocked_overlap_or_cooldown"] == 1


def test_cooldown_blocks_immediate_reentry_after_exit():
    bars = [
        _bar(0, close=100.0, high=101.0, low=98.0),
        _bar(1, close=104.0, high=106.0, low=100.0),
        _bar(2, close=100.0, high=101.0, low=98.0),
        _bar(3, close=104.0, high=106.0, low=100.0),
    ]
    states = [
        _state(trigger=True),
        _state(),
        _state(trigger=True),
        _state(),
    ]
    cfg = CompositeBacktestConfig(
        cooldown_bars=1,
        simulation=TradeSimulationParams(
            slippage_pct=0.0,
            fee_pct=0.0,
            max_hold_bars=10,
        ),
    )

    result = run_indicator_composite_backtest(bars, states, cfg)

    assert result["signal_count"] == 2
    assert result["trade_count"] == 1
    assert result["blocked_overlap_or_cooldown"] == 1


def test_existing_fee_and_slippage_model_remain_active():
    bars = [
        _bar(0, close=100.0, high=101.0, low=98.0),
        _bar(1, close=104.0, high=106.0, low=100.0),
    ]
    states = [_state(trigger=True), _state()]
    result = run_indicator_composite_backtest(bars, states)

    trade = result["trades"][0]
    assert trade["fees"] > 0
    assert trade["slippage_cost"] > 0
    assert trade["net_pnl"] < trade["gross_pnl"]


def test_length_mismatch_fails_closed():
    with pytest.raises(ValueError, match="same length"):
        run_indicator_composite_backtest(
            [_bar(0), _bar(1)],
            [_state()],
        )


def test_negative_cooldown_is_rejected():
    cfg = CompositeBacktestConfig(cooldown_bars=-1)
    with pytest.raises(ValueError, match="non-negative"):
        cfg.validate()


def test_non_positive_max_risk_is_rejected():
    cfg = CompositeBacktestConfig(max_risk_pct=0.0)
    with pytest.raises(ValueError, match="positive"):
        cfg.validate()
