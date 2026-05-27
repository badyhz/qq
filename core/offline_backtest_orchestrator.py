"""Offline backtest orchestrator — pure functions, no I/O.

Coordinates the full backtest pipeline:
  1. Read CSV data (chunked)
  2. Generate signals
  3. Simulate trades
  4. Compute metrics
  5. Score and grade
  6. Build bundle

All functions are pure — no file I/O, no network.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from core.historical_ohlcv_schema import OHLCVColumnMapping
from core.historical_ohlcv_chunked_reader import (
    deduplicate_bars,
    read_ohlcv_chunks,
    validate_ohlcv_chunk,
)
from core.walk_forward_split_engine import split_rolling, split_expanding
from core.offline_breakout_signal_engine import BreakoutSignalParams, scan_breakout_signals
from core.offline_backtest_trade_simulator import (
    TradeOutcome,
    TradeSimulationParams,
    simulate_trade,
)
from core.offline_backtest_metrics_engine import compute_run_metrics, compute_aggregate_metrics
from core.offline_shadow_scorecard import grade_run


def run_backtest_on_bars(
    bars: Sequence[dict],
    signal_params: BreakoutSignalParams | None = None,
    sim_params: TradeSimulationParams | None = None,
) -> Dict[str, Any]:
    """Run a full backtest on a list of bar dicts.

    Returns a dict with keys:
        signals, trades, metrics, scorecard
    """
    signals = scan_breakout_signals(bars, signal_params)
    trades: List[Dict[str, Any]] = []
    for sig in signals:
        outcome = simulate_trade(
            signal={
                "signal_id": sig.signal_id,
                "entry_bar_index": sig.bar_index,
                "entry_price": sig.entry_price,
                "stop_price": sig.stop_price,
                "tp_price": sig.tp_price,
            },
            bars=bars,
            params=sim_params,
        )
        trades.append({
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
        })

    metrics = compute_run_metrics(trades)
    scorecard = grade_run(metrics)

    return {
        "signal_count": len(signals),
        "trade_count": len(trades),
        "signals": [vars(s) for s in signals],
        "trades": trades,
        "metrics": metrics,
        "scorecard": scorecard,
    }


def run_walk_forward_backtest(
    bars: Sequence[dict],
    split_mode: str = "rolling",
    train_pct: float = 0.7,
    test_pct: float = 0.2,
    n_splits: int = 3,
    signal_params: BreakoutSignalParams | None = None,
    sim_params: TradeSimulationParams | None = None,
) -> Dict[str, Any]:
    """Run walk-forward backtest on bar data.

    Returns dict with keys:
        split_mode, splits, per_split_results, aggregate_metrics
    """
    if split_mode == "expanding":
        splits = split_expanding(bars, train_pct, test_pct, n_splits)
    else:
        splits = split_rolling(bars, train_pct, test_pct, n_splits)

    from core.walk_forward_split_engine import SplitType

    test_splits = [s for s in splits if s.split_type == SplitType.TEST]
    per_split_results = []

    for ts in test_splits:
        test_bars = list(bars[ts.start_index:ts.end_index])
        if not test_bars:
            continue
        result = run_backtest_on_bars(test_bars, signal_params, sim_params)
        result["split_id"] = ts.split_id
        result["start_index"] = ts.start_index
        result["end_index"] = ts.end_index
        per_split_results.append(result)

    run_metrics_list = [r["metrics"] for r in per_split_results]
    agg = compute_aggregate_metrics(run_metrics_list)

    return {
        "split_mode": split_mode,
        "split_count": len(splits),
        "test_split_count": len(test_splits),
        "per_split_results": per_split_results,
        "aggregate_metrics": agg,
    }
