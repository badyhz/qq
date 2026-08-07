from __future__ import annotations

import pytest

from core.indicator_composite_backtest import (
    ENTRY_EXECUTION_CONTRACT,
    CompositeBacktestConfig,
    run_indicator_composite_ablation,
    run_indicator_composite_backtest,
)
from core.offline_backtest_trade_simulator import TradeSimulationParams
from core.paper_trading.data_source import MarketBar
from core.paper_trading.indicator_composite_strategy import (
    AccelerationRegime,
    HigherTimeframeTrend,
    IndicatorCompositeState,
)


def _bar(
    index: int,
    *,
    open_: float | None = None,
    close: float = 100.0,
    high: float = 101.0,
    low: float = 99.0,
) -> MarketBar:
    return MarketBar(
        timestamp=float(index * 900),
        open=close if open_ is None else open_,
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


def _zero_friction_config(*, cooldown_bars: int = 0) -> CompositeBacktestConfig:
    return CompositeBacktestConfig(
        cooldown_bars=cooldown_bars,
        simulation=TradeSimulationParams(
            slippage_pct=0.0,
            fee_pct=0.0,
            max_hold_bars=10,
        ),
    )


def test_closed_signal_enters_next_bar_open_and_checks_that_bar():
    bars = [
        _bar(0, open_=99.0, close=100.0, high=101.0, low=98.0),
        # Signal is known only after bar 0 closes. Entry is bar 1 open=100.5.
        # Bar 1 itself then reaches the 2R target.
        _bar(1, open_=100.5, close=105.0, high=106.0, low=99.5),
        _bar(2, open_=105.0, close=105.0, high=106.0, low=104.0),
    ]
    states = [_state(trigger=True), _state(), _state()]

    result = run_indicator_composite_backtest(
        bars,
        states,
        _zero_friction_config(),
    )

    assert result["signal_count"] == 1
    assert result["trade_count"] == 1
    assert result["blocked_risk_gate"] == 0
    signal = result["signals"][0]
    assert signal["signal_bar_index"] == 0
    assert signal["entry_bar_index"] == 1
    assert signal["entry_price"] == pytest.approx(100.5)
    assert signal["entry_execution"] == "bar_open"
    assert signal["entry_execution_contract"] == ENTRY_EXECUTION_CONTRACT
    assert result["entry_execution_contract"] == ENTRY_EXECUTION_CONTRACT
    assert result["trades"][0]["entry_bar_index"] == 1
    assert result["trades"][0]["exit_bar_index"] == 1
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


def test_final_bar_signal_is_not_executable():
    bars = [_bar(0), _bar(1)]
    states = [_state(), _state(trigger=True)]

    result = run_indicator_composite_backtest(bars, states)

    assert result["signal_count"] == 0
    assert result["trade_count"] == 0
    assert result["blocked_no_next_bar"] == 1


def test_next_open_gap_below_signal_stop_is_blocked_not_crashed():
    bars = [
        _bar(0, close=100.0, high=101.0, low=98.0),
        _bar(1, open_=97.0, close=98.0, high=99.0, low=96.0),
    ]
    states = [_state(trigger=True), _state()]

    result = run_indicator_composite_backtest(bars, states)

    assert result["signal_count"] == 0
    assert result["trade_count"] == 0
    assert result["blocked_invalid_execution"] == 1


def test_shadow_risk_gate_blocks_wide_stop_signal():
    bars = [
        _bar(0, close=100.0, high=101.0, low=80.0),
        _bar(1, open_=100.0, close=101.0, high=102.0, low=99.0),
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
        _bar(1, open_=100.0, close=101.0, high=102.0, low=99.0),
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
        _bar(1, open_=100.5, close=100.5, high=101.0, low=99.5),
        _bar(2, open_=101.0, close=105.0, high=106.0, low=100.0),
        _bar(3, open_=105.0, close=105.0, high=106.0, low=104.0),
    ]
    states = [
        _state(trigger=True),
        _state(trigger=True),
        _state(),
        _state(),
    ]

    result = run_indicator_composite_backtest(
        bars,
        states,
        _zero_friction_config(),
    )

    assert result["signal_count"] == 2
    assert result["trade_count"] == 1
    assert result["trades"][0]["exit_bar_index"] == 2
    assert result["blocked_overlap_or_cooldown"] == 1


def test_cooldown_blocks_reentry_after_exit():
    bars = [
        _bar(0, close=100.0, high=101.0, low=98.0),
        _bar(1, open_=100.5, close=100.5, high=101.0, low=99.5),
        _bar(2, open_=101.0, close=105.0, high=106.0, low=100.0),
        _bar(3, open_=100.5, close=101.0, high=102.0, low=100.0),
        _bar(4, open_=101.0, close=105.0, high=106.0, low=100.0),
    ]
    states = [
        _state(trigger=True),
        _state(),
        _state(trigger=True),
        _state(),
        _state(),
    ]

    result = run_indicator_composite_backtest(
        bars,
        states,
        _zero_friction_config(cooldown_bars=1),
    )

    assert result["signal_count"] == 2
    assert result["trade_count"] == 1
    assert result["blocked_overlap_or_cooldown"] == 1


def test_existing_fee_and_slippage_model_remain_active():
    bars = [
        _bar(0, close=100.0, high=101.0, low=98.0),
        _bar(1, open_=100.5, close=100.5, high=101.0, low=99.5),
        _bar(2, open_=101.0, close=105.0, high=106.0, low=100.0),
    ]
    states = [_state(trigger=True), _state(), _state()]
    result = run_indicator_composite_backtest(bars, states)

    trade = result["trades"][0]
    assert trade["fees"] > 0
    assert trade["slippage_cost"] > 0
    assert trade["net_pnl"] < trade["gross_pnl"]


def test_ablation_identifies_accelerator_filter_effect():
    bars = [
        _bar(0, close=100.0, high=101.0, low=98.0),
        _bar(1, open_=100.5, close=100.5, high=101.0, low=99.5),
        _bar(2, open_=101.0, close=105.0, high=106.0, low=100.0),
    ]
    states = [
        _state(trigger=True, regime=AccelerationRegime.IDLE),
        _state(),
        _state(),
    ]

    ablation = run_indicator_composite_ablation(
        bars,
        states,
        _zero_friction_config(),
    )
    variants = {entry["variant"]: entry["result"] for entry in ablation["variants"]}

    assert variants["A_BOTTOM_ONLY"]["signal_count"] == 1
    assert variants["A_BOTTOM_ONLY"]["trade_count"] == 1
    assert variants["B_BOTTOM_ACCELERATOR"]["signal_count"] == 0
    assert variants["C_BOTTOM_ACCELERATOR_HTF"]["signal_count"] == 0
    assert ablation["comparisons"][0]["added_component"] == "market_accelerator"
    assert ablation["comparisons"][0]["delta"]["signal_count_delta"] == -1


def test_ablation_identifies_higher_timeframe_filter_effect():
    bars = [
        _bar(0, close=100.0, high=101.0, low=98.0),
        _bar(1, open_=100.5, close=100.5, high=101.0, low=99.5),
        _bar(2, open_=101.0, close=105.0, high=106.0, low=100.0),
    ]
    states = [
        _state(
            trigger=True,
            regime=AccelerationRegime.START,
            trend=HigherTimeframeTrend.DOWN,
        ),
        _state(),
        _state(),
    ]

    ablation = run_indicator_composite_ablation(
        bars,
        states,
        _zero_friction_config(),
    )
    variants = {entry["variant"]: entry["result"] for entry in ablation["variants"]}

    assert variants["A_BOTTOM_ONLY"]["trade_count"] == 1
    assert variants["B_BOTTOM_ACCELERATOR"]["trade_count"] == 1
    assert variants["C_BOTTOM_ACCELERATOR_HTF"]["trade_count"] == 0
    assert ablation["comparisons"][1]["added_component"] == "higher_timeframe_trend"
    assert ablation["comparisons"][1]["delta"]["trade_count_delta"] == -1
    assert ablation["same_bars"] is True
    assert ablation["same_friction_config"] is True
    assert ablation["entry_execution_contract"] == ENTRY_EXECUTION_CONTRACT
    assert ablation["dynamic_exit_variant_included"] is False
    assert ablation["orders_enabled"] is False


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
