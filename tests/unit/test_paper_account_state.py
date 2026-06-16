"""Tests for paper account state."""
from __future__ import annotations

import pytest
from core.paper_trading.order_plan import OrderPlan, OrderSide, OrderStatus
from core.paper_trading.account_state import AccountState


def _plan(plan_id="P-001", symbol="BTCUSDT", side=OrderSide.BUY,
          entry=50000, sl=49000, tp=53000, size=0.1):
    return OrderPlan(
        plan_id=plan_id, symbol=symbol, side=side,
        entry_price=entry, stop_loss=sl, take_profit=tp,
        invalidation_price=sl * 0.99, risk_amount=100,
        position_size=size, status=OrderStatus.WAITING_FOR_HUMAN_APPROVAL,
    )


class TestAccountState:
    def test_initial_state(self):
        acct = AccountState()
        assert acct.starting_balance == 100000.0
        assert acct.available_balance == 100000.0
        assert acct.reserved_margin == 0.0
        assert acct.realized_pnl == 0.0
        assert acct.open_plan_count == 0
        assert acct.equity == 100000.0

    def test_reserve_margin(self):
        acct = AccountState()
        plan = _plan(entry=50000, size=0.1)
        acct.reserve_margin(plan)
        assert acct.reserved_margin == 5000.0
        assert acct.available_balance == 95000.0
        assert acct.open_plan_count == 1

    def test_close_plan_with_profit(self):
        acct = AccountState()
        plan = _plan(entry=50000, size=0.1)
        acct.reserve_margin(plan)
        acct.close_plan(plan, pnl=500.0)
        assert acct.open_plan_count == 0
        assert acct.reserved_margin == 0.0
        assert acct.realized_pnl == 500.0
        assert acct.available_balance == 100500.0
        assert acct.consecutive_losses == 0

    def test_close_plan_with_loss(self):
        acct = AccountState()
        plan = _plan(entry=50000, size=0.1)
        acct.reserve_margin(plan)
        acct.close_plan(plan, pnl=-300.0)
        assert acct.open_plan_count == 0
        assert acct.realized_pnl == -300.0
        assert acct.available_balance == 99700.0
        assert acct.consecutive_losses == 1
        assert acct.daily_loss == 300.0

    def test_consecutive_losses_cooldown(self):
        acct = AccountState(consecutive_loss_cooldown=3)
        for i in range(3):
            plan = _plan(plan_id=f"P-{i}", entry=50000, size=0.1)
            acct.reserve_margin(plan)
            acct.close_plan(plan, pnl=-100.0)
        assert acct.consecutive_losses == 3
        assert acct.is_cooling_down

    def test_cooldown_resets_on_win(self):
        acct = AccountState(consecutive_loss_cooldown=3)
        # Two losses
        for i in range(2):
            plan = _plan(plan_id=f"P-{i}", entry=50000, size=0.1)
            acct.reserve_margin(plan)
            acct.close_plan(plan, pnl=-100.0)
        assert acct.consecutive_losses == 2
        assert not acct.is_cooling_down
        # Win resets
        plan = _plan(plan_id="P-win", entry=50000, size=0.1)
        acct.reserve_margin(plan)
        acct.close_plan(plan, pnl=200.0)
        assert acct.consecutive_losses == 0

    def test_max_open_plans(self):
        acct = AccountState(max_open_plans=2)
        acct.reserve_margin(_plan(plan_id="P-1"))
        acct.reserve_margin(_plan(plan_id="P-2"))
        allowed, reason = acct.can_open_new_plan()
        assert not allowed
        assert "Max open plans" in reason

    def test_daily_loss_limit(self):
        acct = AccountState(max_daily_loss=500.0)
        plan = _plan()
        acct.reserve_margin(plan)
        acct.close_plan(plan, pnl=-600.0)
        allowed, reason = acct.can_open_new_plan()
        assert not allowed
        assert "Daily loss limit" in reason

    def test_total_exposure(self):
        acct = AccountState()
        acct.reserve_margin(_plan(plan_id="P-1", entry=50000, size=0.5))
        assert acct.total_exposure == 25000.0
        acct.reserve_margin(_plan(plan_id="P-2", entry=50000, size=0.5))
        assert acct.total_exposure == 50000.0

    def test_reset_daily(self):
        acct = AccountState()
        plan = _plan()
        acct.reserve_margin(plan)
        acct.close_plan(plan, pnl=-300.0)
        assert acct.daily_loss == 300.0
        acct.reset_daily()
        assert acct.daily_loss == 0.0

    def test_summary(self):
        acct = AccountState()
        s = acct.summary()
        assert s["starting_balance"] == 100000.0
        assert s["open_plan_count"] == 0
        assert s["cooldown_active"] is False

    def test_equity_with_open_plans(self):
        acct = AccountState()
        plan = _plan(entry=50000, size=0.1)
        acct.reserve_margin(plan)
        # equity = available + reserved + unrealized (0 for new plan)
        assert acct.equity == 100000.0
