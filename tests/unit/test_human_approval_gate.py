"""Tests for human approval gate."""
from __future__ import annotations
import pytest
from core.paper_trading.order_plan import OrderPlan, OrderSide, OrderStatus
from core.paper_trading.human_approval_gate import HumanApprovalGate


def _planned_plan():
    return OrderPlan(
        plan_id="G-001", symbol="BTCUSDT", side=OrderSide.BUY,
        entry_price=50000, stop_loss=49000, take_profit=53000,
        invalidation_price=49500, risk_amount=100, position_size=0.1,
        status=OrderStatus.PLANNED_ONLY,
    )


def _waiting_plan():
    return _planned_plan().with_status(OrderStatus.WAITING_FOR_HUMAN_APPROVAL)


class TestHumanApprovalGate:
    def setup_method(self):
        self.gate = HumanApprovalGate()

    def test_submit_for_approval(self):
        result = self.gate.submit_for_approval(_planned_plan())
        assert result.status == OrderStatus.WAITING_FOR_HUMAN_APPROVAL

    def test_submit_non_planned_raises(self):
        with pytest.raises(ValueError, match="PLANNED_ONLY"):
            self.gate.submit_for_approval(_waiting_plan())

    def test_submit_zero_position_raises(self):
        plan = OrderPlan(
            plan_id="G-002", symbol="BTCUSDT", side=OrderSide.BUY,
            entry_price=50000, stop_loss=49000, take_profit=53000,
            invalidation_price=49500, risk_amount=0, position_size=0,
        )
        with pytest.raises(ValueError, match="zero position"):
            self.gate.submit_for_approval(plan)

    def test_approve_waiting_plan(self):
        result = self.gate.approve(_waiting_plan())
        assert result.status == OrderStatus.WAITING_FOR_HUMAN_APPROVAL

    def test_approve_non_waiting_raises(self):
        with pytest.raises(ValueError, match="WAITING_FOR_HUMAN_APPROVAL"):
            self.gate.approve(_planned_plan())

    def test_cancel_plan(self):
        result = self.gate.cancel(_waiting_plan())
        assert result.status == OrderStatus.CANCELLED

    def test_cancel_already_cancelled_raises(self):
        plan = _waiting_plan().with_status(OrderStatus.CANCELLED)
        with pytest.raises(ValueError, match="CANCELLED"):
            self.gate.cancel(plan)

    def test_cancel_closed_raises(self):
        plan = _waiting_plan().with_status(OrderStatus.SIMULATED_CLOSED)
        with pytest.raises(ValueError, match="SIMULATED_CLOSED"):
            self.gate.cancel(plan)

    def test_get_pending_plans(self):
        plans = [_planned_plan(), _waiting_plan(), _waiting_plan()]
        pending = self.gate.get_pending_plans(plans)
        assert len(pending) == 2

    def test_gate_summary(self):
        plans = [_planned_plan(), _waiting_plan(), _waiting_plan()]
        summary = self.gate.gate_summary(plans)
        assert summary["total"] == 3
        assert summary["pending_approval"] == 2
        assert summary["statuses"]["PLANNED_ONLY"] == 1

    def test_gate_summary_empty(self):
        summary = self.gate.gate_summary([])
        assert summary["total"] == 0
        assert summary["pending_approval"] == 0
