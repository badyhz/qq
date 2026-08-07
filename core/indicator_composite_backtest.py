"""Thin offline backtest adapter for INDICATOR_COMPOSITE_V1.

This module intentionally reuses the repository's existing trade simulator,
metrics engine and scorecard.  It does not implement a second execution engine.

V1 scope:
- long-only composite entry decisions;
- one open simulated position at a time (no overlapping exposures);
- optional post-exit cooldown;
- existing fee/slippage/max-hold behavior via TradeSimulationParams;
- fixed stop/take-profit lifecycle for the first entry-quality backtest.

Iron Top / accelerator-deceleration dynamic exits are deliberately reported as
not yet applied.  They will be layered on after the entry cohort is measurable,
without changing the underlying signal formula or historical population.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from core.offline_backtest_metrics_engine import compute_run_metrics
from core.offline_backtest_trade_simulator import (
    TradeSimulationParams,
    simulate_trade,
)
from core.offline_shadow_scorecard import grade_run
from core.paper_trading.data_source import MarketBar
from core.paper_trading.indicator_composite_strategy import (
    IndicatorCompositeConfig,
    IndicatorCompositeState,
    evaluate_long_entry,
)


@dataclass(frozen=True)
class CompositeBacktestConfig:
    cooldown_bars: int = 0
    simulation: TradeSimulationParams = TradeSimulationParams()
    strategy: IndicatorCompositeConfig = IndicatorCompositeConfig()

    def validate(self) -> None:
        if self.cooldown_bars < 0:
            raise ValueError("cooldown_bars must be non-negative")
        self.strategy.validate()


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


def run_indicator_composite_backtest(
    bars: Sequence[MarketBar],
    states: Sequence[IndicatorCompositeState],
    config: CompositeBacktestConfig | None = None,
) -> dict:
    """Backtest already-normalized composite states on historical bars.

    ``states[i]`` must have been computed using information available no later
    than ``bars[i]``.  This adapter never looks ahead when deciding whether a
    signal exists; only the existing trade simulator scans future bars to
    determine that signal's outcome.
    """
    cfg = config or CompositeBacktestConfig()
    cfg.validate()
    if len(bars) != len(states):
        raise ValueError("bars and states must have the same length")

    bar_dicts = [_bar_dict(bar) for bar in bars]
    trades: list[dict] = []
    signals: list[dict] = []
    filtered_count = 0
    blocked_overlap_or_cooldown = 0
    unavailable_until = -1

    for index, (bar, state) in enumerate(zip(bars, states)):
        decision = evaluate_long_entry(
            state=state,
            entry_price=float(bar.close),
            signal_low=float(bar.low),
            config=cfg.strategy,
        )
        if not decision.should_enter:
            filtered_count += 1
            continue

        signal = {
            "signal_id": f"indicator_composite_v1_{index}",
            "entry_bar_index": index,
            "entry_price": decision.entry_price,
            "stop_price": decision.stop_price,
            "tp_price": decision.take_profit_price,
            "priority": decision.priority,
            "watch_state": decision.watch_state,
            "reasons": list(decision.reasons),
        }
        signals.append(signal)

        if index <= unavailable_until:
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
    # Reuse the existing scorecard but supply the fields it expects and that
    # compute_run_metrics intentionally keeps under its own names.
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
        "blocked_overlap_or_cooldown": blocked_overlap_or_cooldown,
        "signals": signals,
        "trades": trades,
        "metrics": metrics,
        "scorecard": scorecard,
        "cooldown_bars": cfg.cooldown_bars,
        "dynamic_exit_overlay_applied": False,
        "execution_mode": "offline_backtest_only",
        "orders_enabled": False,
    }
