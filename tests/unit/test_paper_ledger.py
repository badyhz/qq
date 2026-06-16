"""Tests for paper ledger."""
from __future__ import annotations
import pytest
from core.paper_trading.order_plan import OrderPlan, OrderSide, OrderStatus, ExitReason
from core.paper_trading.paper_ledger import PaperLedger, LedgerEntry


def _entry(pnl, rr=0.0, reason=ExitReason.TAKE_PROFIT):
    plan = OrderPlan(
        plan_id="L-001", symbol="BTCUSDT", side=OrderSide.BUY,
        entry_price=50000, stop_loss=49000, take_profit=53000,
        invalidation_price=49500, risk_amount=100, position_size=0.1,
        status=OrderStatus.SIMULATED_CLOSED,
    )
    return LedgerEntry(
        plan=plan, entry_bar=0, exit_bar=1,
        exit_price=51000, exit_reason=reason,
        pnl=pnl, rr_actual=rr,
    )


class TestPaperLedger:
    def test_empty_ledger(self):
        ledger = PaperLedger()
        assert ledger.total_trades == 0
        assert ledger.win_rate == 0.0
        assert ledger.total_pnl == 0.0

    def test_record_entry(self):
        ledger = PaperLedger()
        ledger.record(_entry(100, 1.0))
        assert ledger.total_trades == 1

    def test_win_rate(self):
        ledger = PaperLedger()
        ledger.record(_entry(100, 1.0))
        ledger.record(_entry(-50, -0.5))
        ledger.record(_entry(200, 2.0))
        assert ledger.win_rate == pytest.approx(2 / 3)

    def test_winners_losers(self):
        ledger = PaperLedger()
        ledger.record(_entry(100))
        ledger.record(_entry(-50))
        ledger.record(_entry(0))
        assert ledger.winners == 1
        assert ledger.losers == 1
        assert ledger.breakeven == 1

    def test_total_pnl(self):
        ledger = PaperLedger()
        ledger.record(_entry(100))
        ledger.record(_entry(-30))
        assert ledger.total_pnl == 70

    def test_average_rr(self):
        ledger = PaperLedger()
        ledger.record(_entry(100, 2.0))
        ledger.record(_entry(-50, -1.0))
        assert ledger.average_rr == pytest.approx(0.5)

    def test_max_drawdown(self):
        ledger = PaperLedger()
        ledger.record(_entry(100))
        ledger.record(_entry(-200))
        ledger.record(_entry(50))
        assert ledger.max_drawdown == 200  # peak 100, cumulative -100, dd=200

    def test_consecutive_losses(self):
        ledger = PaperLedger()
        ledger.record(_entry(100))
        ledger.record(_entry(-50))
        ledger.record(_entry(-30))
        ledger.record(_entry(-20))
        ledger.record(_entry(100))
        assert ledger.consecutive_losses == 3

    def test_exit_reason_distribution(self):
        ledger = PaperLedger()
        ledger.record(_entry(100, reason=ExitReason.TAKE_PROFIT))
        ledger.record(_entry(-50, reason=ExitReason.STOP_LOSS))
        ledger.record(_entry(30, reason=ExitReason.TAKE_PROFIT))
        dist = ledger.exit_reason_distribution
        assert dist["TAKE_PROFIT"] == 2
        assert dist["STOP_LOSS"] == 1

    def test_summary(self):
        ledger = PaperLedger()
        ledger.record(_entry(100, 1.0, ExitReason.TAKE_PROFIT))
        ledger.record(_entry(-50, -0.5, ExitReason.STOP_LOSS))
        s = ledger.summary()
        assert s["total_trades"] == 2
        assert s["win_rate"] == pytest.approx(0.5)
        assert s["total_pnl"] == 50
