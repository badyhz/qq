"""Thin offline backtest adapter for INDICATOR_COMPOSITE_V1.

This module intentionally reuses the repository's existing trade simulator,
metrics engine, scorecard and TradeIntent risk gate. It does not implement a
second execution engine.

Execution contract:
- all indicator state is computed from a fully closed signal bar ``i``;
- an accepted signal can only enter at bar ``i+1`` open;
- the existing simulator's explicit ``bar_open`` mode applies stop/target checks
  from that entry bar onward;
- a signal on the final dataset bar is unexecutable and never counted as a
  trade.

V1 also provides a deterministic A/B/C entry ablation matrix on identical bars
and friction assumptions. Iron Top / accelerator-deceleration dynamic exits are
not yet applied; they remain a later overlay experiment.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from core.offline_backtest_metrics_engine import compute_run_metrics
from core.offline_backtest_trade_simulator import (
    TradeSimulationParams,
    simulate_trade,
)
from core.offline_shadow_scorecard import grade_run
from core.paper_trading.data_source import MarketBar
from core.paper_trading.indicator_composite_strategy import (
    AccelerationRegime,
    HigherTimeframeTrend,
    IndicatorCompositeConfig,
    IndicatorCompositeState,
    evaluate_long_entry,
)
from core.paper_trading.trade_intent_risk_gate import validate_trade_intent


ENTRY_EXECUTION_CONTRACT = "closed_signal_next_bar_open_v1"


@dataclass(frozen=True)
class CompositeBacktestConfig:
    cooldown_bars: int = 0
    max_risk_pct: float = 0.5
    simulation: TradeSimulationParams = TradeSimulationParams()
    strategy: IndicatorCompositeConfig = IndicatorCompositeConfig()

    def validate(self) -> None:
        if self.cooldown_bars < 0:
            raise ValueError("cooldown_bars must be non-negative")
        if self.max_risk_pct <= 0:
            raise ValueError("max_risk_pct must be positive")
        self.strategy.validate()


ABLATION_VARIANTS = (
    "A_BOTTOM_ONLY",
    "B_BOTTOM_ACCELERATOR",
    "C_BOTTOM_ACCELERATOR_HTF",
)


def _bar_dict(bar: MarketBar) -> dict:
    return {
        "open": float(bar.open),
        "high": float(bar.high),
        "low": float(bar.low),
        "close": float(bar.close),
        "volume": float(bar.volume),
        "timestamp": float(bar.timestamp),
        "symbol": str(bar.symbol),
        "timeframe": str(bar.timeframe),
    }


def _outcome_dict(outcome) -> dict:
    return {
        "trade_id": outcome.trade_id,
        "signal_id": outcome.signal_id,
        "entry_bar_index": outcome.entry_bar_index,
        "exit_bar_index": outcome.exit_bar_index,
        "entry_price": outcome.entry_price,
        "exit_price": outcome.exit_price,
        "exit_reason": outcome.exit_reason,
        "realized_r": outcome.realized_r,
        "gross_pnl": outcome.gross_pnl,
        "fees": outcome.fees,
        "slippage_cost": outcome.slippage_cost,
        "net_pnl": outcome.net_pnl,
        "mfe_r": outcome.mfe_r,
        "mae_r": outcome.mae_r,
        "hold_bars": outcome.hold_bars,
    }


def _entry_filters_ready(state: IndicatorCompositeState) -> bool:
    return (
        state.bottom_treasure_trigger
        and state.acceleration_regime in {
            AccelerationRegime.START,
            AccelerationRegime.FAST,
        }
        and state.higher_timeframe_trend != HigherTimeframeTrend.DOWN
    )


def _risk_gate_for_decision(decision, max_risk_pct: float):
    assert decision.entry_price is not None
    assert decision.stop_price is not None
    assert decision.take_profit_price is not None
    entry = float(decision.entry_price)
    stop = float(decision.stop_price)
    take_profit = float(decision.take_profit_price)
    risk_distance_pct = (entry - stop) / entry * 100.0
    reward_distance_pct = (take_profit - entry) / entry * 100.0
    intent_like = {
        "execution_mode": "shadow_only",
        "side": "LONG",
        "intent_status": "SHADOW_READY",
        "rr_ratio": float(decision.rr_ratio),
        "risk_distance_pct": risk_distance_pct,
        "reward_distance_pct": reward_distance_pct,
        "max_risk_pct": float(max_risk_pct),
        "entry_price": entry,
        "stop_loss": stop,
        "take_profit": take_profit,
    }
    return validate_trade_intent(intent_like), risk_distance_pct, reward_distance_pct


def run_indicator_composite_backtest(
    bars: Sequence[MarketBar],
    states: Sequence[IndicatorCompositeState],
    config: CompositeBacktestConfig | None = None,
) -> dict:
    """Backtest normalized states using closed-signal -> next-open execution."""
    cfg = config or CompositeBacktestConfig()
    cfg.validate()
    if len(bars) != len(states):
        raise ValueError("bars and states must have the same length")

    bar_dicts = [_bar_dict(bar) for bar in bars]
    trades: list[dict] = []
    signals: list[dict] = []
    filtered_count = 0
    blocked_no_next_bar = 0
    blocked_invalid_execution = 0
    blocked_risk_gate = 0
    blocked_overlap_or_cooldown = 0
    unavailable_until = -1

    for signal_index, (signal_bar, state) in enumerate(zip(bars, states)):
        if signal_index + 1 >= len(bars):
            if _entry_filters_ready(state):
                blocked_no_next_bar += 1
            else:
                filtered_count += 1
            continue

        entry_index = signal_index + 1
        entry_bar = bars[entry_index]
        try:
            decision = evaluate_long_entry(
                state=state,
                entry_price=float(entry_bar.open),
                signal_low=float(signal_bar.low),
                config=cfg.strategy,
            )
        except ValueError as exc:
            # A next-bar gap can invalidate a signal-low stop by opening at or
            # below that stop. Treat this as a missed/invalid execution rather
            # than crashing the experiment. Other configuration errors surface.
            if "computed stop" in str(exc):
                blocked_invalid_execution += 1
                continue
            raise

        if not decision.should_enter:
            filtered_count += 1
            continue

        gate, risk_distance_pct, reward_distance_pct = _risk_gate_for_decision(
            decision, cfg.max_risk_pct
        )
        signal = {
            "signal_id": f"indicator_composite_v1_{signal_index}",
            "signal_bar_index": signal_index,
            "entry_bar_index": entry_index,
            "entry_execution": "bar_open",
            "entry_execution_contract": ENTRY_EXECUTION_CONTRACT,
            "entry_price": decision.entry_price,
            "stop_price": decision.stop_price,
            "tp_price": decision.take_profit_price,
            "rr_ratio": decision.rr_ratio,
            "risk_distance_pct": round(risk_distance_pct, 6),
            "reward_distance_pct": round(reward_distance_pct, 6),
            "priority": decision.priority,
            "watch_state": decision.watch_state,
            "reasons": list(decision.reasons),
            "risk_gate_status": gate.status,
            "risk_gate_reasons": list(gate.reasons),
        }
        signals.append(signal)

        if not gate.passed:
            blocked_risk_gate += 1
            continue

        if entry_index <= unavailable_until:
            blocked_overlap_or_cooldown += 1
            continue

        outcome = simulate_trade(
            signal=signal,
            bars=bar_dicts,
            params=cfg.simulation,
        )
        trade = _outcome_dict(outcome)
        trades.append(trade)
        unavailable_until = outcome.exit_bar_index + cfg.cooldown_bars

    metrics = compute_run_metrics(trades)
    metrics_for_grade = dict(metrics)
    metrics_for_grade["candidate_count"] = len(signals)
    metrics_for_grade["sample_quality_score"] = metrics.get(
        "sample_adequacy_score", 0.0
    )
    scorecard = grade_run(metrics_for_grade)

    return {
        "strategy_id": "indicator_composite_v1",
        "signal_count": len(signals),
        "trade_count": len(trades),
        "filtered_count": filtered_count,
        "blocked_no_next_bar": blocked_no_next_bar,
        "blocked_invalid_execution": blocked_invalid_execution,
        "blocked_risk_gate": blocked_risk_gate,
        "blocked_overlap_or_cooldown": blocked_overlap_or_cooldown,
        "signals": signals,
        "trades": trades,
        "metrics": metrics,
        "scorecard": scorecard,
        "cooldown_bars": cfg.cooldown_bars,
        "max_risk_pct": cfg.max_risk_pct,
        "entry_execution_contract": ENTRY_EXECUTION_CONTRACT,
        "dynamic_exit_overlay_applied": False,
        "execution_mode": "offline_backtest_only",
        "orders_enabled": False,
    }


def _states_for_ablation(
    states: Sequence[IndicatorCompositeState],
    variant: str,
) -> tuple[IndicatorCompositeState, ...]:
    """Remove only requested entry filters while preserving Bottom triggers."""
    if variant not in ABLATION_VARIANTS:
        raise ValueError(f"unknown ablation variant: {variant}")

    output: list[IndicatorCompositeState] = []
    for state in states:
        if variant == "A_BOTTOM_ONLY":
            acceleration = AccelerationRegime.START
            trend = HigherTimeframeTrend.NEUTRAL
        elif variant == "B_BOTTOM_ACCELERATOR":
            acceleration = state.acceleration_regime
            trend = HigherTimeframeTrend.NEUTRAL
        else:
            acceleration = state.acceleration_regime
            trend = state.higher_timeframe_trend

        output.append(IndicatorCompositeState(
            bottom_treasure_trigger=state.bottom_treasure_trigger,
            acceleration_regime=acceleration,
            higher_timeframe_trend=trend,
            iron_top_strength=state.iron_top_strength,
            atr=state.atr,
        ))
    return tuple(output)


def _finite_delta(current: float | int, previous: float | int) -> float | None:
    current_f = float(current)
    previous_f = float(previous)
    if not math.isfinite(current_f) or not math.isfinite(previous_f):
        return None
    return round(current_f - previous_f, 6)


def _ablation_delta(previous: dict, current: dict) -> dict:
    previous_metrics = previous.get("metrics", {})
    current_metrics = current.get("metrics", {})
    return {
        "signal_count_delta": int(current.get("signal_count", 0))
        - int(previous.get("signal_count", 0)),
        "trade_count_delta": int(current.get("trade_count", 0))
        - int(previous.get("trade_count", 0)),
        "expectancy_r_delta": _finite_delta(
            current_metrics.get("expectancy_r", 0.0),
            previous_metrics.get("expectancy_r", 0.0),
        ),
        "profit_factor_delta": _finite_delta(
            current_metrics.get("profit_factor", 0.0),
            previous_metrics.get("profit_factor", 0.0),
        ),
        "max_drawdown_r_delta": _finite_delta(
            current_metrics.get("max_drawdown_r", 0.0),
            previous_metrics.get("max_drawdown_r", 0.0),
        ),
    }


def run_indicator_composite_ablation(
    bars: Sequence[MarketBar],
    states: Sequence[IndicatorCompositeState],
    config: CompositeBacktestConfig | None = None,
) -> dict:
    """Run A/B/C entry-filter ablation on identical data and frictions."""
    cfg = config or CompositeBacktestConfig()
    cfg.validate()
    if len(bars) != len(states):
        raise ValueError("bars and states must have the same length")

    definitions = {
        "A_BOTTOM_ONLY": ["bottom_treasure"],
        "B_BOTTOM_ACCELERATOR": ["bottom_treasure", "market_accelerator"],
        "C_BOTTOM_ACCELERATOR_HTF": [
            "bottom_treasure",
            "market_accelerator",
            "higher_timeframe_trend",
        ],
    }
    variants = []
    for variant in ABLATION_VARIANTS:
        result = run_indicator_composite_backtest(
            bars,
            _states_for_ablation(states, variant),
            cfg,
        )
        variants.append({
            "variant": variant,
            "entry_components": definitions[variant],
            "result": result,
        })

    comparisons = []
    for previous, current in zip(variants, variants[1:]):
        comparisons.append({
            "from": previous["variant"],
            "to": current["variant"],
            "added_component": current["entry_components"][-1],
            "delta": _ablation_delta(previous["result"], current["result"]),
        })

    return {
        "experiment_id": "indicator_composite_entry_ablation_v1",
        "variant_order": list(ABLATION_VARIANTS),
        "variants": variants,
        "comparisons": comparisons,
        "same_bars": True,
        "same_friction_config": True,
        "entry_execution_contract": ENTRY_EXECUTION_CONTRACT,
        "dynamic_exit_variant_included": False,
        "orders_enabled": False,
    }
