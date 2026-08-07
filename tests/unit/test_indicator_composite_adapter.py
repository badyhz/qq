from __future__ import annotations

from core.paper_trading.aicoin_indicator_ports import (
    BottomTreasureResult,
    IronTopResult,
)
from core.paper_trading.indicator_composite_adapter import (
    build_long_signal_candidate,
    compose_state,
)
from core.paper_trading.indicator_composite_strategy import (
    AccelerationRegime,
    HigherTimeframeTrend,
)
from core.paper_trading.trade_intent import build_trade_intent
from scripts.run_enabled_strategies import _candidate_to_plan


def _bottom(triggered: bool = True) -> BottomTreasureResult:
    return BottomTreasureResult(
        triggered=triggered,
        new_low=triggered,
        treasure_above_threshold=triggered,
        close_reclaimed_previous_low=triggered,
        treasure_value=20.0 if triggered else 0.0,
        threshold=10.0,
    )


def _iron(strength: int = 0) -> IronTopResult:
    return IronTopResult(
        strength=strength,
        new_high_30=strength > 0,
        new_high_55=strength > 1,
        new_high_30_only=strength == 1,
        speed_5=1.0,
        speed_avg=0.5,
        speed_sd=0.1,
        speed_extreme=strength > 0,
        weak_close=strength > 0,
    )


def test_compose_state_preserves_independent_indicator_outputs():
    state = compose_state(
        bottom_treasure=_bottom(),
        acceleration_regime=AccelerationRegime.FAST,
        higher_timeframe_trend=HigherTimeframeTrend.UP,
        iron_top=_iron(2),
        atr=2.5,
    )

    assert state.bottom_treasure_trigger is True
    assert state.acceleration_regime == AccelerationRegime.FAST
    assert state.higher_timeframe_trend == HigherTimeframeTrend.UP
    assert state.iron_top_strength == 2
    assert state.atr == 2.5


def test_filtered_state_does_not_emit_existing_pipeline_candidate():
    state = compose_state(
        bottom_treasure=_bottom(False),
        acceleration_regime=AccelerationRegime.START,
        higher_timeframe_trend=HigherTimeframeTrend.NEUTRAL,
    )

    candidate = build_long_signal_candidate(
        strategy_id="indicator_composite_v1",
        symbol="BTCUSDT",
        timeframe="15m",
        state=state,
        entry_price=100.0,
        signal_low=97.0,
    )

    assert candidate is None


def test_composite_candidate_reuses_signal_candidate_contract():
    state = compose_state(
        bottom_treasure=_bottom(),
        acceleration_regime=AccelerationRegime.START,
        higher_timeframe_trend=HigherTimeframeTrend.NEUTRAL,
        atr=2.0,
    )

    candidate = build_long_signal_candidate(
        strategy_id="indicator_composite_v1",
        symbol="BTCUSDT",
        timeframe="15m",
        state=state,
        entry_price=100.0,
        signal_low=97.0,
        signal_bar_close_time="2026-08-07T10:00:00.000+00:00",
        signal_bar_contract_version="closed_bar_v1",
    )

    assert candidate is not None
    assert candidate.strategy_id == "indicator_composite_v1"
    assert candidate.strategy_type == "indicator_composite_v1"
    assert candidate.direction == "LONG_OBSERVE"
    assert candidate.watch_state == "LONG_READY"
    assert candidate.macd_state == "NOT_USED"
    assert candidate.signal_bar_contract_version == "closed_bar_v1"
    assert 0 < candidate.risk_distance_pct < 5
    assert candidate.reward_distance_pct > candidate.risk_distance_pct


def test_candidate_flows_into_existing_shadow_trade_intent_without_new_engine():
    state = compose_state(
        bottom_treasure=_bottom(),
        acceleration_regime=AccelerationRegime.FAST,
        higher_timeframe_trend=HigherTimeframeTrend.UP,
        atr=2.0,
    )
    candidate = build_long_signal_candidate(
        strategy_id="indicator_composite_v1",
        symbol="BTCUSDT",
        timeframe="15m",
        state=state,
        entry_price=100.0,
        signal_low=97.0,
        signal_bar_close_time="2026-08-07T10:00:00.000+00:00",
        signal_bar_contract_version="closed_bar_v1",
    )
    assert candidate is not None

    plan = _candidate_to_plan(candidate)
    intent = build_trade_intent(
        plan,
        date_str="2026-08-07",
        paper_equity=10000.0,
        max_risk_pct=0.5,
    )

    assert intent.strategy_id == "indicator_composite_v1"
    assert intent.side == "LONG"
    assert intent.execution_mode == "shadow_only"
    assert intent.intent_status == "SHADOW_READY"
    assert intent.entry_price == candidate.entry_observation
    assert intent.stop_loss == candidate.invalidation_level
    assert intent.take_profit == candidate.take_profit_observation
    assert intent.signal_bar_contract_version == "closed_bar_v1"
