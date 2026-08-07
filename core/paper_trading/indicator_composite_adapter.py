"""Adapter from INDICATOR_COMPOSITE_V1 decisions to existing shadow schemas.

This module is intentionally small: it does not calculate the underlying
indicator formulas and it does not place or simulate orders.  It translates a
fully-normalized composite state into the existing ``SignalCandidate`` shape so
that the proven trade-intent/risk-gate/paper-position pipeline can be reused.
"""
from __future__ import annotations

from typing import Optional

from core.paper_trading.aicoin_indicator_ports import (
    BottomTreasureResult,
    IronTopResult,
)
from core.paper_trading.indicator_composite_strategy import (
    AccelerationRegime,
    HigherTimeframeTrend,
    IndicatorCompositeConfig,
    IndicatorCompositeState,
    evaluate_long_entry,
)
from core.paper_trading.strategy_registry import SignalCandidate


STRATEGY_TYPE = "indicator_composite_v1"


def compose_state(
    *,
    bottom_treasure: BottomTreasureResult,
    acceleration_regime: AccelerationRegime,
    higher_timeframe_trend: HigherTimeframeTrend,
    iron_top: IronTopResult | None = None,
    atr: float | None = None,
) -> IndicatorCompositeState:
    """Combine independently-tested indicator outputs into one strategy state."""
    if not isinstance(acceleration_regime, AccelerationRegime):
        raise TypeError("acceleration_regime must be AccelerationRegime")
    if not isinstance(higher_timeframe_trend, HigherTimeframeTrend):
        raise TypeError("higher_timeframe_trend must be HigherTimeframeTrend")
    return IndicatorCompositeState(
        bottom_treasure_trigger=bottom_treasure.triggered,
        acceleration_regime=acceleration_regime,
        higher_timeframe_trend=higher_timeframe_trend,
        iron_top_strength=iron_top.strength if iron_top is not None else 0,
        atr=atr,
    )


def build_long_signal_candidate(
    *,
    strategy_id: str,
    symbol: str,
    timeframe: str,
    state: IndicatorCompositeState,
    entry_price: float,
    signal_low: float,
    signal_bar_close_time: str | None = None,
    signal_bar_contract_version: str = "legacy_missing",
    config: IndicatorCompositeConfig | None = None,
) -> Optional[SignalCandidate]:
    """Return an existing-pipeline candidate, or ``None`` when entry is filtered.

    The legacy ``SignalCandidate`` schema contains MACD/RSI fields because it
    predates this strategy.  For INDICATOR_COMPOSITE_V1 those fields are marked
    ``NOT_USED`` rather than populated with misleading synthetic values.
    """
    decision = evaluate_long_entry(
        state=state,
        entry_price=entry_price,
        signal_low=signal_low,
        config=config,
    )
    if not decision.should_enter:
        return None

    assert decision.entry_price is not None
    assert decision.stop_price is not None
    assert decision.take_profit_price is not None

    risk = decision.entry_price - decision.stop_price
    reward = decision.take_profit_price - decision.entry_price
    risk_pct = risk / decision.entry_price * 100.0
    reward_pct = reward / decision.entry_price * 100.0

    return SignalCandidate(
        strategy_id=strategy_id,
        strategy_type=STRATEGY_TYPE,
        symbol=symbol,
        timeframe=timeframe,
        watch_state=decision.watch_state,
        setup_type="INDICATOR_COMPOSITE_LONG",
        direction=decision.direction,
        priority=decision.priority,
        last_close=round(entry_price, 8),
        entry_observation=decision.entry_price,
        invalidation_level=decision.stop_price,
        take_profit_observation=decision.take_profit_price,
        rr_ratio=decision.rr_ratio,
        risk_distance_pct=round(risk_pct, 4),
        reward_distance_pct=round(reward_pct, 4),
        turning_score=0,
        weakness_score=0,
        risk_score=0,
        macd_state="NOT_USED",
        rsi_state="NOT_USED",
        trend_bias=f"HTF_{state.higher_timeframe_trend.value}",
        volume_state="ACCELERATOR_INPUT",
        reasons=list(decision.reasons),
        risk_notes=(
            f"composite_v1; accelerator={state.acceleration_regime.value}; "
            f"iron_top_strength={state.iron_top_strength}"
        ),
        signal_bar_close_time=signal_bar_close_time,
        signal_bar_contract_version=signal_bar_contract_version,
    )
