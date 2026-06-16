"""Paper trading ledger — local simulation only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from collections import Counter

from core.paper_trading.order_plan import OrderPlan, OrderStatus, ExitReason


@dataclass
class LedgerEntry:
    plan: OrderPlan
    entry_bar: int
    exit_bar: int
    exit_price: float
    exit_reason: ExitReason
    pnl: float
    rr_actual: float = 0.0


@dataclass
class PaperLedger:
    entries: List[LedgerEntry] = field(default_factory=list)

    def record(self, entry: LedgerEntry) -> None:
        self.entries.append(entry)

    @property
    def total_trades(self) -> int:
        return len(self.entries)

    @property
    def winners(self) -> int:
        return sum(1 for e in self.entries if e.pnl > 0)

    @property
    def losers(self) -> int:
        return sum(1 for e in self.entries if e.pnl < 0)

    @property
    def breakeven(self) -> int:
        return sum(1 for e in self.entries if e.pnl == 0)

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.winners / self.total_trades

    @property
    def total_pnl(self) -> float:
        return sum(e.pnl for e in self.entries)

    @property
    def average_rr(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return sum(e.rr_actual for e in self.entries) / self.total_trades

    @property
    def max_drawdown(self) -> float:
        if not self.entries:
            return 0.0
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        for e in self.entries:
            cumulative += e.pnl
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd
        return max_dd

    @property
    def consecutive_losses(self) -> int:
        max_streak = 0
        current = 0
        for e in self.entries:
            if e.pnl < 0:
                current += 1
                max_streak = max(max_streak, current)
            else:
                current = 0
        return max_streak

    @property
    def exit_reason_distribution(self) -> Dict[str, int]:
        counter = Counter(e.exit_reason.value for e in self.entries)
        return dict(counter)

    @property
    def rejected_signals(self) -> int:
        return sum(1 for e in self.entries
                   if e.plan.status == OrderStatus.CANCELLED)

    def summary(self) -> Dict[str, Any]:
        return {
            "total_trades": self.total_trades,
            "winners": self.winners,
            "losers": self.losers,
            "breakeven": self.breakeven,
            "win_rate": round(self.win_rate, 4),
            "total_pnl": round(self.total_pnl, 2),
            "average_rr": round(self.average_rr, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "consecutive_losses": self.consecutive_losses,
            "rejected_signals": self.rejected_signals,
            "exit_reasons": self.exit_reason_distribution,
        }
