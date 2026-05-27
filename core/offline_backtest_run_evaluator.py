"""Offline backtest run evaluator. Pure functions, no I/O.

Evaluates a single backtest run: applies split window, runs signal engine,
simulates trades, aggregates metrics into a RunResult.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, Sequence, Tuple

from core.offline_backtest_signal_engine import detect_breakout_signals, apply_cooldown
from core.offline_backtest_trade_simulator import TradeOutcome, simulate_trade


@dataclass(frozen=True)
class RunResult:
    """Frozen result of a single backtest run."""

    run_id: str
    symbol: str
    timeframe: str
    param_id: str
    split_id: int
    trades: Tuple[TradeOutcome, ...]
    trade_count: int
    metrics: Dict[str, Any]

    def __post_init__(self) -> None:
        if self.trade_count != len(self.trades):
            raise ValueError(
                f"trade_count ({self.trade_count}) must equal len(trades) ({len(self.trades)})"
            )


def _aggregate_metrics(trades: Sequence[TradeOutcome]) -> Dict[str, Any]:
    """Compute aggregate metrics from a list of trade outcomes."""
    if not trades:
        return {
            "total_trades": 0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate": 0.0,
            "total_net_pnl": 0.0,
            "total_gross_pnl": 0.0,
            "total_fees": 0.0,
            "total_slippage_cost": 0.0,
            "avg_r": 0.0,
            "max_r": 0.0,
            "min_r": 0.0,
            "avg_hold_bars": 0.0,
            "max_mfe_r": 0.0,
            "max_mae_r": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
        }

    wins = [t for t in trades if t.net_pnl > 0]
    losses = [t for t in trades if t.net_pnl <= 0]
    total_net = sum(t.net_pnl for t in trades)
    total_gross = sum(t.gross_pnl for t in trades)
    total_fees = sum(t.fees for t in trades)
    total_slippage = sum(t.slippage_cost for t in trades)
    avg_r = sum(t.realized_r for t in trades) / len(trades)
    avg_hold = sum(t.hold_bars for t in trades) / len(trades)

    gross_wins = sum(t.net_pnl for t in wins)
    gross_losses = abs(sum(t.net_pnl for t in losses))
    profit_factor = gross_wins / gross_losses if gross_losses > 0 else float("inf") if gross_wins > 0 else 0.0

    win_rate = len(wins) / len(trades) if trades else 0.0
    avg_win = gross_wins / len(wins) if wins else 0.0
    avg_loss = gross_losses / len(losses) if losses else 0.0
    expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

    return {
        "total_trades": len(trades),
        "win_count": len(wins),
        "loss_count": len(losses),
        "win_rate": round(win_rate, 6),
        "total_net_pnl": round(total_net, 6),
        "total_gross_pnl": round(total_gross, 6),
        "total_fees": round(total_fees, 6),
        "total_slippage_cost": round(total_slippage, 6),
        "avg_r": round(avg_r, 6),
        "max_r": round(max(t.realized_r for t in trades), 6),
        "min_r": round(min(t.realized_r for t in trades), 6),
        "avg_hold_bars": round(avg_hold, 2),
        "max_mfe_r": round(max(t.mfe_r for t in trades), 6),
        "max_mae_r": round(max(t.mae_r for t in trades), 6),
        "profit_factor": round(profit_factor, 6),
        "expectancy": round(expectancy, 6),
    }


def evaluate_run(
    bars: Sequence[dict],
    split,
    params,
    symbol: str = "",
    timeframe: str = "",
) -> RunResult:
    """Evaluate a single backtest run.

    Takes bars as input (list), applies split window, runs signal engine,
    simulates trades, aggregates metrics.

    Parameters
    ----------
    bars : Sequence[dict]
        Full bar data as list of dicts.
    split : WalkForwardSplit
        The split defining the evaluation window (typically TEST split).
    params : BacktestParameterSet
        Parameters for signal detection and trade simulation.
    symbol : str
        Symbol identifier.
    timeframe : str
        Timeframe identifier.

    Returns
    -------
    RunResult
    """
    # Slice bars to split window
    window_bars = bars[split.start_index:split.end_index]

    if not window_bars:
        return RunResult(
            run_id=str(uuid.uuid4()),
            symbol=symbol,
            timeframe=timeframe,
            param_id=params.param_id,
            split_id=split.split_id,
            trades=(),
            trade_count=0,
            metrics=_aggregate_metrics([]),
        )

    # Detect signals in the window
    signals = detect_breakout_signals(window_bars, params)
    signals = apply_cooldown(signals, params.cooldown_bars)

    # Simulate trades — convert Signal objects to dict format for simulate_trade
    trades = []
    for sig in signals:
        # Compute stop/tp from params R-multiples
        stop_distance = sig.entry_price * (params.stop_loss_r / 100.0)
        tp_distance = sig.entry_price * (params.take_profit_r / 100.0)
        sig_dict = {
            "signal_id": sig.signal_id,
            "entry_bar_index": sig.bar_index,
            "entry_price": sig.entry_price,
            "stop_price": sig.entry_price - stop_distance,
            "tp_price": sig.entry_price + tp_distance,
        }
        trade = simulate_trade(sig_dict, window_bars, None)
        trades.append(trade)

    return RunResult(
        run_id=str(uuid.uuid4()),
        symbol=symbol,
        timeframe=timeframe,
        param_id=params.param_id,
        split_id=split.split_id,
        trades=tuple(trades),
        trade_count=len(trades),
        metrics=_aggregate_metrics(trades),
    )
