from __future__ import annotations

import pytest

from core.paper_trading.indicator_composite_strategy import (
    AccelerationRegime,
    ExitAction,
    HigherTimeframeTrend,
    IndicatorCompositeConfig,
    IndicatorCompositeState,
    evaluate_long_entry,
    evaluate_long_exit,
    staged_take_profit_plan,
)


def _state(**overrides) -> IndicatorCompositeState:
    data = {
        "bottom_treasure_trigger": True,
        "acceleration_regime": AccelerationRegime.START,
        "higher_timeframe_trend": HigherTimeframeTrend.NEUTRAL,
        "iron_top_strength": 0,
        "atr": 2.0,
    }
    data.update(overrides)
    return IndicatorCompositeState(**data)


def test_long_entry_requires_bottom_treasure_trigger():
    decision = evaluate_long_entry(
        state=_state(bottom_treasure_trigger=False),
        entry_price=100.0,
        signal_low=95.0,
    )
    assert decision.should_enter is False
    assert decision.direction == "NO_TRADE"
    assert "BOTTOM_TREASURE_NOT_TRIGGERED" in decision.reasons


def test_start_acceleration_allows_long_entry():
    decision = evaluate_long_entry(
        state=_state(acceleration_regime=AccelerationRegime.START),
        entry_price=100.0,
        signal_low=95.0,
    )
    assert decision.should_enter is True
    assert decision.direction == "LONG_OBSERVE"
    assert decision.watch_state == "LONG_READY"
    assert decision.priority == "MEDIUM"
    assert decision.stop_price == pytest.approx(94.905)
    assert decision.take_profit_price == pytest.approx(110.19)
    assert decision.rr_ratio == 2.0


def test_fast_acceleration_is_high_priority():
    decision = evaluate_long_entry(
        state=_state(acceleration_regime=AccelerationRegime.FAST),
        entry_price=100.0,
        signal_low=95.0,
    )
    assert decision.should_enter is True
    assert decision.priority == "HIGH"


def test_extreme_acceleration_blocks_chasing():
    decision = evaluate_long_entry(
        state=_state(acceleration_regime=AccelerationRegime.EXTREME),
        entry_price=100.0,
        signal_low=95.0,
    )
    assert decision.should_enter is False
    assert "ACCELERATOR_EXTREME_NO_CHASE" in decision.reasons


def test_higher_timeframe_downtrend_blocks_entry():
    decision = evaluate_long_entry(
        state=_state(higher_timeframe_trend=HigherTimeframeTrend.DOWN),
        entry_price=100.0,
        signal_low=95.0,
    )
    assert decision.should_enter is False
    assert "HIGHER_TIMEFRAME_DOWN" in decision.reasons


def test_atr_stop_mode_uses_configured_multiple():
    cfg = IndicatorCompositeConfig(
        stop_mode="atr",
        atr_stop_multiple=1.5,
        initial_take_profit_r=2.0,
    )
    decision = evaluate_long_entry(
        state=_state(atr=2.0),
        entry_price=100.0,
        signal_low=95.0,
        config=cfg,
    )
    assert decision.should_enter is True
    assert decision.stop_price == 97.0
    assert decision.take_profit_price == 106.0


def test_atr_stop_mode_rejects_missing_atr():
    cfg = IndicatorCompositeConfig(stop_mode="atr")
    with pytest.raises(ValueError, match="positive atr"):
        evaluate_long_entry(
            state=_state(atr=None),
            entry_price=100.0,
            signal_low=95.0,
            config=cfg,
        )


def test_strong_iron_top_exits_long():
    decision = evaluate_long_exit(state=_state(iron_top_strength=2))
    assert decision.action == ExitAction.EXIT
    assert decision.reason == "IRON_TOP_STRONG"


def test_early_iron_top_reduces_long():
    decision = evaluate_long_exit(state=_state(iron_top_strength=1))
    assert decision.action == ExitAction.REDUCE
    assert decision.reason == "IRON_TOP_EARLY"


def test_accelerator_deceleration_exits_remaining_long():
    decision = evaluate_long_exit(
        state=_state(acceleration_regime=AccelerationRegime.DECELERATING)
    )
    assert decision.action == ExitAction.EXIT
    assert decision.reason == "ACCELERATOR_DECELERATING"


def test_no_exit_overlay_holds():
    decision = evaluate_long_exit(state=_state())
    assert decision.action == ExitAction.HOLD


def test_staged_take_profit_plan_is_research_metadata_only():
    assert staged_take_profit_plan() == ((1.0, 0.30), (2.0, 0.30))
    assert sum(fraction for _r, fraction in staged_take_profit_plan()) == pytest.approx(0.60)
