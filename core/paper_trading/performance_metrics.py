"""Performance metrics for paper trading replay results."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from core.paper_trading.paper_ledger import PaperLedger, LedgerEntry


@dataclass(frozen=True)
class PerformanceMetrics:
    total_trades: int
    winners: int
    losers: int
    breakevens: int
    win_rate: float
    total_pnl: float
    avg_pnl_per_trade: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    max_consecutive_losses: int
    avg_rr_actual: float
    expectancy: float  # avg_win * win_rate - avg_loss * (1 - win_rate)


def compute_metrics(ledger: PaperLedger) -> PerformanceMetrics:
    """Compute performance metrics from a paper ledger."""
    summary = ledger.summary()
    entries = ledger.entries

    winners = summary["winners"]
    losers = summary["losers"]
    breakevens = summary["breakeven"]
    total = winners + losers + breakevens
    total_pnl = summary["total_pnl"]

    win_pnls = [e.pnl for e in entries if e.pnl > 0]
    loss_pnls = [e.pnl for e in entries if e.pnl < 0]

    avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0.0
    avg_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0.0

    gross_profit = sum(win_pnls)
    gross_loss = abs(sum(loss_pnls))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0

    rr_values = [e.rr_actual for e in entries if e.rr_actual != 0]
    avg_rr = sum(rr_values) / len(rr_values) if rr_values else 0.0

    win_rate = summary["win_rate"]
    expectancy = avg_win * win_rate + avg_loss * (1 - win_rate)

    return PerformanceMetrics(
        total_trades=total,
        winners=winners,
        losers=losers,
        breakevens=breakevens,
        win_rate=win_rate,
        total_pnl=total_pnl,
        avg_pnl_per_trade=total_pnl / total if total > 0 else 0.0,
        avg_win=avg_win,
        avg_loss=avg_loss,
        profit_factor=profit_factor,
        max_drawdown=summary["max_drawdown"],
        max_consecutive_losses=summary["consecutive_losses"],
        avg_rr_actual=avg_rr,
        expectancy=expectancy,
    )
