"""Build no-lookahead INDICATOR_COMPOSITE_V1 states from indicator ports.

This builder is deliberately explicit about the Bottom Treasure formula source.
The only fully automatic source currently implemented is the versioned
``bottom_treasure_recovered_v0`` research formula.  The later SMMA variant is
not guessed; callers may instead supply exact external Bottom Treasure triggers
once that final formula is recovered.
"""
from __future__ import annotations

from typing import Sequence

from core.paper_trading.aicoin_indicator_ports import evaluate_iron_top
from core.paper_trading.bottom_treasure_recovered_v0 import (
    calculate_recovered_bottom_treasure,
)
from core.paper_trading.data_source import MarketBar
from core.paper_trading.indicator_composite_strategy import (
    HigherTimeframeTrend,
    IndicatorCompositeState,
)
from core.paper_trading.market_accelerator_port import (
    MarketAcceleratorConfig,
    calculate_market_accelerator,
)
from core.paper_trading.market_accelerator_regime import (
    AcceleratorRegimeConfig,
    classify_accelerator_series,
)


def _iron_top_strength_by_index(bars: Sequence[MarketBar]) -> list[int]:
    strengths: list[int] = []
    for index in range(len(bars)):
        try:
            result = evaluate_iron_top(bars[:index + 1])
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
    """Build states using recovered-v0 Bottom Treasure + recovered accelerator.

    ``higher_timeframe_trends[i]`` must be calculated from information available
    by ``bars[i]``.  Requiring the caller to provide it prevents this builder
    from quietly replacing a true higher-timeframe filter with same-timeframe
    information.
    """
    if len(bars) != len(higher_timeframe_trends):
        raise ValueError("bars and higher_timeframe_trends must have the same length")
    if not bars:
        return ()
    if any(not isinstance(value, HigherTimeframeTrend) for value in higher_timeframe_trends):
        raise TypeError("all higher_timeframe_trends must be HigherTimeframeTrend")

    bottoms = calculate_recovered_bottom_treasure(bars)
    accelerator = calculate_market_accelerator(bars, accelerator_config)
    regimes = classify_accelerator_series(accelerator.points, regime_config)
    iron_strengths = _iron_top_strength_by_index(bars)

    states = []
    for index in range(len(bars)):
        states.append(IndicatorCompositeState(
            bottom_treasure_trigger=bottoms[index].buy_signal,
            acceleration_regime=regimes[index].regime,
            higher_timeframe_trend=higher_timeframe_trends[index],
            iron_top_strength=iron_strengths[index],
            atr=None,
        ))
    return tuple(states)


def build_external_bottom_composite_states(
    bars: Sequence[MarketBar],
    bottom_triggers: Sequence[bool],
    higher_timeframe_trends: Sequence[HigherTimeframeTrend],
    *,
    accelerator_config: MarketAcceleratorConfig | None = None,
    regime_config: AcceleratorRegimeConfig | None = None,
) -> tuple[IndicatorCompositeState, ...]:
    """Build states using exact externally supplied Bottom Treasure triggers.

    This is the intended bridge for the later final SMMA-based AiCoin formula:
    once its exact port exists, its boolean trigger series can be fed here
    without changing accelerator, Iron Top, backtest, or shadow adapters.
    """
    if not (len(bars) == len(bottom_triggers) == len(higher_timeframe_trends)):
        raise ValueError("bars, bottom_triggers and trends must have the same length")
    if any(not isinstance(value, bool) for value in bottom_triggers):
        raise TypeError("all bottom_triggers must be bool")
    if any(not isinstance(value, HigherTimeframeTrend) for value in higher_timeframe_trends):
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
