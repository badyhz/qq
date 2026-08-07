"""INDICATOR_COMPOSITE_V1 assembly and existing-pipeline adapter.

This module owns the thin glue between independently-tested indicator outputs,
``IndicatorCompositeState`` and the repository's existing ``SignalCandidate``
contract. It does not place or simulate orders.

Research state builders live here as well so the strategy does not accumulate a
separate one-file state-builder abstraction. The recovered-v0 builder remains
explicitly distinct from the future final Bottom Treasure formula.
"""
from __future__ import annotations

from typing import Optional, Sequence

from core.paper_trading.aicoin_indicator_ports import (
    BottomTreasureResult,
    IronTopResult,
    calculate_recovered_bottom_treasure,
    evaluate_iron_top,
)
from core.paper_trading.data_source import MarketBar
from core.paper_trading.indicator_composite_strategy import (
    AccelerationRegime,
    HigherTimeframeTrend,
    IndicatorCompositeConfig,
    IndicatorCompositeState,
    evaluate_long_entry,
)
from core.paper_trading.market_accelerator_port import (
    AcceleratorRegimeConfig,
    MarketAcceleratorConfig,
    calculate_market_accelerator,
    classify_accelerator_series,
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


def _iron_top_strength_by_index(bars: Sequence[MarketBar]) -> list[int]:
    strengths: list[int] = []
    for index in range(len(bars)):
        try:
            result = evaluate_iron_top(bars[: index + 1])
        except ValueError:
            strengths.append(0)
        else:
            strengths.append(result.strength)
    return strengths


def build_recovered_v0_composite_states(
    bars: Sequence[MarketBar],
    higher_timeframe_trends: Sequence[HigherTimeframeTrend],
    *,
    accelerator_config: MarketAcceleratorConfig | None = None,
    regime_config: AcceleratorRegimeConfig | None = None,
) -> tuple[IndicatorCompositeState, ...]:
    """Build no-lookahead states using recovered-v0 Bottom Treasure research."""
    if len(bars) != len(higher_timeframe_trends):
        raise ValueError("bars and higher_timeframe_trends must have the same length")
    if not bars:
        return ()
    if any(
        not isinstance(value, HigherTimeframeTrend)
        for value in higher_timeframe_trends
    ):
        raise TypeError("all higher_timeframe_trends must be HigherTimeframeTrend")

    bottoms = calculate_recovered_bottom_treasure(bars)
    accelerator = calculate_market_accelerator(bars, accelerator_config)
    regimes = classify_accelerator_series(accelerator.points, regime_config)
    iron_strengths = _iron_top_strength_by_index(bars)

    return tuple(
        IndicatorCompositeState(
            bottom_treasure_trigger=bottoms[index].buy_signal,
            acceleration_regime=regimes[index].regime,
            higher_timeframe_trend=higher_timeframe_trends[index],
            iron_top_strength=iron_strengths[index],
            atr=None,
        )
        for index in range(len(bars))
    )


def build_external_bottom_composite_states(
    bars: Sequence[MarketBar],
    bottom_triggers: Sequence[bool],
    higher_timeframe_trends: Sequence[HigherTimeframeTrend],
    *,
    accelerator_config: MarketAcceleratorConfig | None = None,
    regime_config: AcceleratorRegimeConfig | None = None,
) -> tuple[IndicatorCompositeState, ...]:
    """Build states from exact externally supplied final Bottom triggers.

    This is the bridge for the later SMMA-based Bottom Treasure formula: once
    its exact trigger series is recovered, accelerator, Iron Top, backtest and
    Shadow adapters do not need to change.
    """
    if not (len(bars) == len(bottom_triggers) == len(higher_timeframe_trends)):
        raise ValueError("bars, bottom_triggers and trends must have the same length")
    if any(not isinstance(value, bool) for value in bottom_triggers):
        raise TypeError("all bottom_triggers must be bool")
    if any(
        not isinstance(value, HigherTimeframeTrend)
        for value in higher_timeframe_trends
    ):
        raise TypeError("all higher_timeframe_trends must be HigherTimeframeTrend")

    accelerator = calculate_market_accelerator(bars, accelerator_config)
    regimes = classify_accelerator_series(accelerator.points, regime_config)
    iron_strengths = _iron_top_strength_by_index(bars)

    return tuple(
        IndicatorCompositeState(
            bottom_treasure_trigger=bottom_triggers[index],
            acceleration_regime=regimes[index].regime,
            higher_timeframe_trend=higher_timeframe_trends[index],
            iron_top_strength=iron_strengths[index],
            atr=None,
        )
        for index in range(len(bars))
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
    predates this strategy. For INDICATOR_COMPOSITE_V1 those fields are marked
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
