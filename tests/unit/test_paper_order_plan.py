"""Tests for paper order plan."""
from __future__ import annotations
import pytest
from core.paper_trading.order_plan import (
    OrderPlan, OrderSide, OrderStatus, ExitReason,
)


class TestOrderPlan:
    def test_create_buy_plan(self):
        plan = OrderPlan(
            plan_id="P-001", symbol="BTCUSDT", side=OrderSide.BUY,
            entry_price=50000.0, stop_loss=49000.0, take_profit=53000.0,
            invalidation_price=49500.0, risk_amount=100.0, position_size=0.1,
        )
        assert plan.status == OrderStatus.PLANNED_ONLY
        assert plan.side == OrderSide.BUY

    def test_create_sell_plan(self):
        plan = OrderPlan(
            plan_id="P-002", symbol="ETHUSDT", side=OrderSide.SELL,
            entry_price=3000.0, stop_loss=3100.0, take_profit=2700.0,
            invalidation_price=3050.0, risk_amount=50.0, position_size=0.5,
        )
        assert plan.side == OrderSide.SELL

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError, match="Invalid status"):
            OrderPlan(
                plan_id="P-003", symbol="BTCUSDT", side=OrderSide.BUY,
                entry_price=50000.0, stop_loss=49000.0, take_profit=53000.0,
                invalidation_price=49500.0, risk_amount=100.0, position_size=0.1,
                status="SUBMITTED",
            )

    def test_invalid_side_raises(self):
        with pytest.raises(ValueError, match="Invalid side"):
            OrderPlan(
                plan_id="P-004", symbol="BTCUSDT", side="HOLD",
                entry_price=50000.0, stop_loss=49000.0, take_profit=53000.0,
                invalidation_price=49500.0, risk_amount=100.0, position_size=0.1,
            )

    def test_negative_entry_raises(self):
        with pytest.raises(ValueError, match="entry_price"):
            OrderPlan(
                plan_id="P-005", symbol="BTCUSDT", side=OrderSide.BUY,
                entry_price=-1.0, stop_loss=49000.0, take_profit=53000.0,
                invalidation_price=49500.0, risk_amount=100.0, position_size=0.1,
            )

    def test_negative_risk_raises(self):
        with pytest.raises(ValueError, match="risk_amount"):
            OrderPlan(
                plan_id="P-006", symbol="BTCUSDT", side=OrderSide.BUY,
                entry_price=50000.0, stop_loss=49000.0, take_profit=53000.0,
                invalidation_price=49500.0, risk_amount=-1.0, position_size=0.1,
            )

    def test_with_status_returns_new_plan(self):
        plan = OrderPlan(
            plan_id="P-007", symbol="BTCUSDT", side=OrderSide.BUY,
            entry_price=50000.0, stop_loss=49000.0, take_profit=53000.0,
            invalidation_price=49500.0, risk_amount=100.0, position_size=0.1,
        )
        closed = plan.with_status(OrderStatus.SIMULATED_CLOSED, ExitReason.TAKE_PROFIT, 200.0)
        assert closed.status == OrderStatus.SIMULATED_CLOSED
        assert closed.exit_reason == ExitReason.TAKE_PROFIT
        assert closed.closed_pnl == 200.0
        assert plan.status == OrderStatus.PLANNED_ONLY  # immutable

    def test_to_dict(self):
        plan = OrderPlan(
            plan_id="P-008", symbol="BTCUSDT", side=OrderSide.BUY,
            entry_price=50000.0, stop_loss=49000.0, take_profit=53000.0,
            invalidation_price=49500.0, risk_amount=100.0, position_size=0.1,
            signal_source="macd_rebound", rr_ratio=3.0,
        )
        d = plan.to_dict()
        assert d["plan_id"] == "P-008"
        assert d["side"] == "BUY"
        assert d["status"] == "PLANNED_ONLY"
        assert d["signal_source"] == "macd_rebound"

    def test_to_dict_closed_plan(self):
        plan = OrderPlan(
            plan_id="P-009", symbol="BTCUSDT", side=OrderSide.BUY,
            entry_price=50000.0, stop_loss=49000.0, take_profit=53000.0,
            invalidation_price=49500.0, risk_amount=100.0, position_size=0.1,
        ).with_status(OrderStatus.SIMULATED_CLOSED, ExitReason.STOP_LOSS, -100.0)
        d = plan.to_dict()
        assert d["exit_reason"] == "STOP_LOSS"
        assert d["closed_pnl"] == -100.0

    def test_valid_statuses(self):
        for status in OrderStatus:
            plan = OrderPlan(
                plan_id="P-010", symbol="BTCUSDT", side=OrderSide.BUY,
                entry_price=50000.0, stop_loss=49000.0, take_profit=53000.0,
                invalidation_price=49500.0, risk_amount=100.0, position_size=0.1,
                status=status,
            )
            assert plan.status == status

    def test_frozen_immutable(self):
        plan = OrderPlan(
            plan_id="P-011", symbol="BTCUSDT", side=OrderSide.BUY,
            entry_price=50000.0, stop_loss=49000.0, take_profit=53000.0,
            invalidation_price=49500.0, risk_amount=100.0, position_size=0.1,
        )
        with pytest.raises(AttributeError):
            plan.plan_id = "CHANGED"
