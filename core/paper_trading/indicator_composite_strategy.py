"""Pure decision contract for INDICATOR_COMPOSITE_V1.

This module deliberately contains no exchange, network, account, order, or
persistence code.  It is the strategy-rule layer that will sit between the
three AiCoin-derived indicators and the existing shadow trade-intent pipeline.

V1 policy agreed for the first implementation:
- long only;
- Bottom Treasure is the entry trigger;
- Market Accelerator confirms a tradable acceleration regime;
- an extreme/no-chase regime blocks new entries;
- a clearly bearish higher-timeframe trend blocks new entries;
- Iron Top is an exit/reduction signal, not a short-entry signal;
- exact indicator formulas are kept outside this decision contract so they can
  be ported and regression-tested independently from lifecycle/risk logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AccelerationRegime(str, Enum):
    """Normalized Market Accelerator / 疾速500 regimes."""

    IDLE = "IDLE"
    START = "START"
    FAST = "FAST"
    EXTREME = "EXTREME"
    DECELERATING = "DECELERATING"


class HigherTimeframeTrend(str, Enum):
    """Minimal higher-timeframe filter used by V1."""

    UP = "UP"
    NEUTRAL = "NEUTRAL"
    DOWN = "DOWN"


class ExitAction(str, Enum):
    """Action recommendation for an already-open long shadow position."""

    HOLD = "HOLD"
    REDUCE = "REDUCE"
    EXIT = "EXIT"


@dataclass(frozen=True)
class IndicatorCompositeConfig:
    """Risk/decision parameters that are independent from indicator formulas."""

    stop_mode: str = "signal_low"  # signal_low | atr
    stop_buffer_pct: float = 0.10
    atr_stop_multiple: float = 1.5
    initial_take_profit_r: float = 2.0
    reduce_iron_top_strength: int = 1
    exit_iron_top_strength: int = 2

    def validate(self) -> None:
        if self.stop_mode not in {"signal_low", "atr"}:
            raise ValueError("stop_mode must be 'signal_low' or 'atr'")
        if self.stop_buffer_pct < 0:
            raise ValueError("stop_buffer_pct must be non-negative")
        if self.atr_stop_multiple <= 0:
            raise ValueError("atr_stop_multiple must be positive")
        if self.initial_take_profit_r <= 0:
            raise ValueError("initial_take_profit_r must be positive")
        if self.reduce_iron_top_strength < 1:
            raise ValueError("reduce_iron_top_strength must be >= 1")
        if self.exit_iron_top_strength < self.reduce_iron_top_strength:
            raise ValueError("exit_iron_top_strength must be >= reduce threshold")


@dataclass(frozen=True)
class IndicatorCompositeState:
    """Normalized outputs from the three indicator formula engines.

    ``bottom_treasure_trigger`` and ``iron_top_strength`` are intentionally
    formula-agnostic here.  Their exact AiCoin formulas will be ported into a
    separate pure indicator module and will feed this state.
    """

    bottom_treasure_trigger: bool
    acceleration_regime: AccelerationRegime
    higher_timeframe_trend: HigherTimeframeTrend
    iron_top_strength: int = 0
    atr: Optional[float] = None


@dataclass(frozen=True)
class CompositeEntryDecision:
    """Long-entry decision expressed in the existing shadow vocabulary."""

    should_enter: bool
    direction: str
    watch_state: str
    priority: str
    entry_price: Optional[float]
    stop_price: Optional[float]
    take_profit_price: Optional[float]
    rr_ratio: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CompositeExitDecision:
    """Exit/reduction decision for an existing long position."""

    action: ExitAction
    reason: str


def _build_stop(
    *,
    entry_price: float,
    signal_low: float,
    atr: Optional[float],
    config: IndicatorCompositeConfig,
) -> float:
    if entry_price <= 0:
        raise ValueError("entry_price must be positive")
    if signal_low <= 0:
        raise ValueError("signal_low must be positive")

    if config.stop_mode == "atr":
        if atr is None or atr <= 0:
            raise ValueError("positive atr is required for atr stop mode")
        stop = entry_price - atr * config.atr_stop_multiple
    else:
        stop = signal_low * (1.0 - config.stop_buffer_pct / 100.0)

    if stop <= 0 or stop >= entry_price:
        raise ValueError("computed stop must be positive and below entry")
    return stop


def evaluate_long_entry(
    *,
    state: IndicatorCompositeState,
    entry_price: float,
    signal_low: float,
    config: IndicatorCompositeConfig | None = None,
) -> CompositeEntryDecision:
    """Evaluate the V1 long-entry contract.

    Entry requires Bottom Treasure + START/FAST acceleration + a non-bearish
    higher-timeframe filter.  EXTREME explicitly means "do not chase".
    Iron Top is not used to create a short entry in V1.
    """
    cfg = config or IndicatorCompositeConfig()
    cfg.validate()

    reasons: list[str] = []
    if not state.bottom_treasure_trigger:
        reasons.append("BOTTOM_TREASURE_NOT_TRIGGERED")
    if state.acceleration_regime not in {
        AccelerationRegime.START,
        AccelerationRegime.FAST,
    }:
        if state.acceleration_regime == AccelerationRegime.EXTREME:
            reasons.append("ACCELERATOR_EXTREME_NO_CHASE")
        else:
            reasons.append("ACCELERATOR_NOT_CONFIRMING")
    if state.higher_timeframe_trend == HigherTimeframeTrend.DOWN:
        reasons.append("HIGHER_TIMEFRAME_DOWN")

    if reasons:
        return CompositeEntryDecision(
            should_enter=False,
            direction="NO_TRADE",
            watch_state="FILTERED",
            priority="LOW",
            entry_price=None,
            stop_price=None,
            take_profit_price=None,
            rr_ratio=0.0,
            reasons=tuple(reasons),
        )

    stop = _build_stop(
        entry_price=entry_price,
        signal_low=signal_low,
        atr=state.atr,
        config=cfg,
    )
    risk = entry_price - stop
    take_profit = entry_price + risk * cfg.initial_take_profit_r
    priority = (
        "HIGH"
        if state.acceleration_regime == AccelerationRegime.FAST
        else "MEDIUM"
    )

    return CompositeEntryDecision(
        should_enter=True,
        direction="LONG_OBSERVE",
        watch_state="LONG_READY",
        priority=priority,
        entry_price=round(entry_price, 8),
        stop_price=round(stop, 8),
        take_profit_price=round(take_profit, 8),
        rr_ratio=round(cfg.initial_take_profit_r, 4),
        reasons=(
            "BOTTOM_TREASURE_TRIGGERED",
            f"ACCELERATOR_{state.acceleration_regime.value}",
            f"HIGHER_TIMEFRAME_{state.higher_timeframe_trend.value}",
        ),
    )


def evaluate_long_exit(
    *,
    state: IndicatorCompositeState,
    config: IndicatorCompositeConfig | None = None,
) -> CompositeExitDecision:
    """Evaluate V1 discretionary exit overlays for an existing long.

    A strong Iron Top signal exits.  A weaker Iron Top signal recommends a
    reduction.  Accelerator deceleration exits the remaining trend position.
    This function never creates a short entry.
    """
    cfg = config or IndicatorCompositeConfig()
    cfg.validate()

    if state.iron_top_strength >= cfg.exit_iron_top_strength:
        return CompositeExitDecision(ExitAction.EXIT, "IRON_TOP_STRONG")
    if state.acceleration_regime == AccelerationRegime.DECELERATING:
        return CompositeExitDecision(ExitAction.EXIT, "ACCELERATOR_DECELERATING")
    if state.iron_top_strength >= cfg.reduce_iron_top_strength:
        return CompositeExitDecision(ExitAction.REDUCE, "IRON_TOP_EARLY")
    return CompositeExitDecision(ExitAction.HOLD, "NO_EXIT_OVERLAY")


def staged_take_profit_plan() -> tuple[tuple[float, float], ...]:
    """Return the research plan for staged exits as (R, fraction) pairs.

    The current production shadow lifecycle has a single take-profit field, so
    this plan is research metadata only until partial-close accounting is
    explicitly implemented and tested.  It must not be interpreted as an
    executable order schedule.
    """
    return ((1.0, 0.30), (2.0, 0.30))
