"""Tests for paper portfolio risk."""
from __future__ import annotations

import pytest
from core.paper_trading.order_plan import OrderPlan, OrderSide, OrderStatus
from core.paper_trading.account_state import AccountState
from core.paper_trading.portfolio_risk import (
    PortfolioRiskConfig, RiskCheckResult, check_portfolio_risk, apply_portfolio_risk,
)


def _plan(plan_id="P-001", symbol="BTCUSDT", side=OrderSide.BUY,
          entry=50000, sl=49000, tp=53000, size=0.1,
          status=OrderStatus.WAITING_FOR_HUMAN_APPROVAL):
    return OrderPlan(
        plan_id=plan_id, symbol=symbol, side=side,
        entry_price=entry, stop_loss=sl, take_profit=tp,
        invalidation_price=sl * 0.99, risk_amount=100,
        position_size=size, status=status,
    )


class TestPortfolioRisk:
    def test_approve_normal(self):
        acct = AccountState()
        config = PortfolioRiskConfig()
        plan = _plan()
        result = check_portfolio_risk(plan, acct, config)
        assert result.approved

    def test_reject_max_open_plans(self):
        acct = AccountState(max_open_plans=1)
        acct.reserve_margin(_plan(plan_id="P-1"))
        config = PortfolioRiskConfig(max_open_plans=1)
        result = check_portfolio_risk(_plan(plan_id="P-2"), acct, config)
        assert not result.approved
        assert "Max open plans" in result.reason

    def test_reject_same_symbol_limit(self):
        acct = AccountState()
        acct.reserve_margin(_plan(plan_id="P-1", symbol="BTCUSDT"))
        acct.reserve_margin(_plan(plan_id="P-2", symbol="BTCUSDT"))
        config = PortfolioRiskConfig(max_same_symbol_plans=2)
        result = check_portfolio_risk(_plan(plan_id="P-3", symbol="BTCUSDT"), acct, config)
        assert not result.approved
        assert "Max 2 plans for BTCUSDT" in result.reason

    def test_reject_duplicate_direction(self):
        acct = AccountState()
        acct.reserve_margin(_plan(plan_id="P-1", symbol="BTCUSDT", side=OrderSide.BUY))
        config = PortfolioRiskConfig(block_duplicate_direction=True)
        result = check_portfolio_risk(
            _plan(plan_id="P-2", symbol="BTCUSDT", side=OrderSide.BUY),
            acct, config,
        )
        assert not result.approved
        assert "Duplicate BUY" in result.reason

    def test_allow_opposite_direction(self):
        acct = AccountState()
        acct.reserve_margin(_plan(plan_id="P-1", symbol="BTCUSDT", side=OrderSide.BUY))
        config = PortfolioRiskConfig(block_duplicate_direction=True)
        result = check_portfolio_risk(
            _plan(plan_id="P-2", symbol="BTCUSDT", side=OrderSide.SELL),
            acct, config,
        )
        assert result.approved

    def test_reject_exposure_limit(self):
        acct = AccountState()
        acct.reserve_margin(_plan(plan_id="P-1", symbol="BTCUSDT", entry=50000, size=0.8))
        config = PortfolioRiskConfig(
            max_total_exposure=50000,
            block_duplicate_direction=False,
        )
        result = check_portfolio_risk(
            _plan(plan_id="P-2", symbol="ETHUSDT", entry=50000, size=0.5),
            acct, config,
        )
        assert not result.approved
        assert "Exposure" in result.reason

    def test_reject_daily_loss(self):
        acct = AccountState(max_daily_loss=500)
        plan = _plan()
        acct.reserve_margin(plan)
        acct.close_plan(plan, pnl=-600)
        config = PortfolioRiskConfig(max_daily_loss=500)
        result = check_portfolio_risk(_plan(plan_id="P-2"), acct, config)
        assert not result.approved
        assert "Daily loss" in result.reason

    def test_reject_cooldown(self):
        acct = AccountState(consecutive_loss_cooldown=2)
        for i in range(2):
            p = _plan(plan_id=f"P-{i}")
            acct.reserve_margin(p)
            acct.close_plan(p, pnl=-100)
        config = PortfolioRiskConfig(consecutive_loss_cooldown=2)
        result = check_portfolio_risk(_plan(plan_id="P-new"), acct, config)
        assert not result.approved
        assert "Cooldown" in result.reason

    def test_apply_risk_approved(self):
        acct = AccountState()
        config = PortfolioRiskConfig()
        plan = _plan()
        result = apply_portfolio_risk(plan, acct, config)
        assert result.status == OrderStatus.WAITING_FOR_HUMAN_APPROVAL

    def test_apply_risk_cancelled(self):
        acct = AccountState(max_open_plans=1)
        acct.reserve_margin(_plan(plan_id="P-1"))
        config = PortfolioRiskConfig(max_open_plans=1)
        result = apply_portfolio_risk(_plan(plan_id="P-2"), acct, config)
        assert result.status == OrderStatus.CANCELLED

    def test_different_symbols_allowed(self):
        acct = AccountState()
        config = PortfolioRiskConfig(max_same_symbol_plans=1)
        acct.reserve_margin(_plan(plan_id="P-1", symbol="BTCUSDT"))
        result = check_portfolio_risk(
            _plan(plan_id="P-2", symbol="ETHUSDT"),
            acct, config,
        )
        assert result.approved

    def test_multiple_symbols_exposure(self):
        acct = AccountState()
        config = PortfolioRiskConfig(max_total_exposure=60000)
        acct.reserve_margin(_plan(plan_id="P-1", symbol="BTCUSDT", entry=50000, size=0.5))
        acct.reserve_margin(_plan(plan_id="P-2", symbol="ETHUSDT", entry=3000, size=2.0))
        # Total exposure: 25000 + 6000 = 31000
        result = check_portfolio_risk(
            _plan(plan_id="P-3", symbol="SOLUSDT", entry=100, size=200),
            acct, config,
        )
        # 31000 + 20000 = 51000 < 60000 → approved
        assert result.approved
