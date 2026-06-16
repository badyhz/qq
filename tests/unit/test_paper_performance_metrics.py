"""Tests for performance metrics computation."""
from __future__ import annotations

import pytest

from core.paper_trading.order_plan import OrderPlan, OrderSide, OrderStatus, ExitReason
from core.paper_trading.paper_ledger import PaperLedger, LedgerEntry
from core.paper_trading.performance_metrics import PerformanceMetrics, compute_metrics


def _make_plan(side=OrderSide.BUY, entry=50000.0):
    return OrderPlan(
        plan_id="P1", symbol="BTCUSDT", side=side,
        entry_price=entry, stop_loss=entry * 0.98,
        take_profit=entry * 1.06, invalidation_price=entry * 0.97,
        risk_amount=100.0, position_size=0.01,
    )


def _entry(pnl, rr=0.0, exit_reason=ExitReason.TAKE_PROFIT):
    return LedgerEntry(
        plan=_make_plan(), entry_bar=0, exit_bar=1,
        exit_price=50000, exit_reason=exit_reason,
        pnl=pnl, rr_actual=rr,
    )


class TestPerformanceMetrics:
    def test_empty_ledger(self):
        ledger = PaperLedger()
        m = compute_metrics(ledger)
        assert m.total_trades == 0
        assert m.winners == 0
        assert m.total_pnl == 0.0
        assert m.win_rate == 0.0
        assert m.profit_factor == 0.0

    def test_single_winner(self):
        ledger = PaperLedger()
        ledger.record(_entry(100.0, rr=2.0))
        m = compute_metrics(ledger)
        assert m.total_trades == 1
        assert m.winners == 1
        assert m.losers == 0
        assert m.win_rate == 1.0
        assert m.total_pnl == 100.0
        assert m.profit_factor == float("inf")

    def test_single_loser(self):
        ledger = PaperLedger()
        ledger.record(_entry(-50.0, rr=-1.0))
        m = compute_metrics(ledger)
        assert m.total_trades == 1
        assert m.losers == 1
        assert m.win_rate == 0.0
        assert m.total_pnl == -50.0
        assert m.profit_factor == 0.0

    def test_mixed_trades(self):
        ledger = PaperLedger()
        ledger.record(_entry(200.0, rr=2.0))
        ledger.record(_entry(-100.0, rr=-1.0))
        ledger.record(_entry(150.0, rr=1.5))
        m = compute_metrics(ledger)
        assert m.total_trades == 3
        assert m.winners == 2
        assert m.losers == 1
        assert m.total_pnl == 250.0
        assert abs(m.win_rate - 2/3) < 0.01
        assert m.profit_factor == 350.0 / 100.0  # 3.5

    def test_breakeven_counted(self):
        ledger = PaperLedger()
        ledger.record(_entry(0.0, rr=0.0, exit_reason=ExitReason.TIME_STOP))
        m = compute_metrics(ledger)
        assert m.breakevens == 1
        assert m.total_trades == 1

    def test_avg_pnl_per_trade(self):
        ledger = PaperLedger()
        ledger.record(_entry(100.0))
        ledger.record(_entry(-50.0))
        m = compute_metrics(ledger)
        assert m.avg_pnl_per_trade == 25.0

    def test_avg_win_avg_loss(self):
        ledger = PaperLedger()
        ledger.record(_entry(200.0))
        ledger.record(_entry(100.0))
        ledger.record(_entry(-50.0))
        ledger.record(_entry(-100.0))
        m = compute_metrics(ledger)
        assert m.avg_win == 150.0
        assert m.avg_loss == -75.0

    def test_max_consecutive_losses(self):
        ledger = PaperLedger()
        ledger.record(_entry(100.0))
        ledger.record(_entry(-10.0))
        ledger.record(_entry(-20.0))
        ledger.record(_entry(-30.0))
        ledger.record(_entry(50.0))
        m = compute_metrics(ledger)
        assert m.max_consecutive_losses == 3

    def test_avg_rr_actual(self):
        ledger = PaperLedger()
        ledger.record(_entry(100.0, rr=2.0))
        ledger.record(_entry(-50.0, rr=-1.0))
        m = compute_metrics(ledger)
        assert m.avg_rr_actual == 0.5

    def test_expectancy(self):
        ledger = PaperLedger()
        ledger.record(_entry(200.0))
        ledger.record(_entry(-100.0))
        m = compute_metrics(ledger)
        # win_rate=0.5, avg_win=200, avg_loss=-100
        # expectancy = 200*0.5 + (-100)*0.5 = 50
        assert m.expectancy == 50.0

    def test_frozen_dataclass(self):
        ledger = PaperLedger()
        ledger.record(_entry(100.0))
        m = compute_metrics(ledger)
        with pytest.raises(AttributeError):
            m.total_trades = 999  # type: ignore

    def test_max_drawdown(self):
        ledger = PaperLedger()
        ledger.record(_entry(100.0))
        ledger.record(_entry(-200.0))  # dd from 100 to -100 = 200
        ledger.record(_entry(50.0))
        m = compute_metrics(ledger)
        assert m.max_drawdown == 200.0
