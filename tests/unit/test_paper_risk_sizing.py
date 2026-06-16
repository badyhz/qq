"""Tests for paper risk sizing."""
from __future__ import annotations
import pytest
from core.paper_trading.order_plan import OrderPlan, OrderSide, OrderStatus
from core.paper_trading.risk_sizing import (
    RiskSizingConfig, RiskSizingResult, calculate_risk, apply_risk_sizing,
)


class TestCalculateRisk:
    def test_basic_buy(self):
        result = calculate_risk(50000, 49000, 53000, RiskSizingConfig())
        assert result.approved is True
        assert result.rr_ratio == 3.0
        assert result.position_size > 0

    def test_basic_sell(self):
        result = calculate_risk(3000, 3100, 2700, RiskSizingConfig(), OrderSide.SELL)
        assert result.approved is True
        assert result.rr_ratio == 3.0

    def test_rr_below_minimum_rejects(self):
        result = calculate_risk(50000, 49000, 50500, RiskSizingConfig(min_rr_ratio=2.0))
        assert result.approved is False
        assert "RR" in result.rejection_reason

    def test_rr_at_minimum_accepts(self):
        result = calculate_risk(50000, 49000, 52000, RiskSizingConfig(min_rr_ratio=2.0))
        assert result.approved is True
        assert result.rr_ratio == 2.0

    def test_zero_risk_per_unit(self):
        result = calculate_risk(50000, 50000, 53000, RiskSizingConfig())
        assert result.approved is False
        assert "Stop loss equals entry" in result.rejection_reason

    def test_negative_prices_rejected(self):
        result = calculate_risk(-1, 49000, 53000, RiskSizingConfig())
        assert result.approved is False

    def test_position_capped_by_max_position_pct(self):
        config = RiskSizingConfig(equity=100000, max_position_pct=5.0, max_margin_cap=999999999)
        result = calculate_risk(100, 90, 130, config)
        assert result.approved is True
        max_value = 100000 * 0.05
        assert result.position_size * 100 <= max_value + 0.01

    def test_position_capped_by_margin_cap(self):
        config = RiskSizingConfig(equity=100000, max_position_pct=100.0, max_margin_cap=5000)
        result = calculate_risk(100, 90, 130, config)
        assert result.approved is True
        assert result.position_size * 100 <= 5000 + 0.01

    def test_risk_amount_calculation(self):
        config = RiskSizingConfig(equity=100000, max_risk_per_trade_pct=1.0)
        result = calculate_risk(50000, 49000, 53000, config)
        assert result.approved is True
        assert result.risk_amount <= 1000.01  # 1% of 100k

    def test_small_risk_trade(self):
        result = calculate_risk(100, 99, 103, RiskSizingConfig())
        assert result.approved is True
        assert result.rr_ratio == 3.0


class TestApplyRiskSizing:
    def test_approves_valid_plan(self):
        plan = OrderPlan(
            plan_id="R-001", symbol="BTCUSDT", side=OrderSide.BUY,
            entry_price=50000, stop_loss=49000, take_profit=53000,
            invalidation_price=49500, risk_amount=0, position_size=0,
        )
        result = apply_risk_sizing(plan, RiskSizingConfig())
        assert result.status == OrderStatus.WAITING_FOR_HUMAN_APPROVAL
        assert result.position_size > 0
        assert result.risk_amount > 0

    def test_cancels_bad_rr(self):
        plan = OrderPlan(
            plan_id="R-002", symbol="BTCUSDT", side=OrderSide.BUY,
            entry_price=50000, stop_loss=49000, take_profit=50500,
            invalidation_price=49500, risk_amount=0, position_size=0,
        )
        result = apply_risk_sizing(plan, RiskSizingConfig(min_rr_ratio=2.0))
        assert result.status == OrderStatus.CANCELLED

    def test_preserves_plan_fields(self):
        plan = OrderPlan(
            plan_id="R-003", symbol="ETHUSDT", side=OrderSide.SELL,
            entry_price=3000, stop_loss=3100, take_profit=2700,
            invalidation_price=3050, risk_amount=0, position_size=0,
            signal_source="macd_rebound",
        )
        result = apply_risk_sizing(plan, RiskSizingConfig())
        assert result.symbol == "ETHUSDT"
        assert result.side == OrderSide.SELL
        assert result.signal_source == "macd_rebound"
        assert result.plan_id == "R-003"
