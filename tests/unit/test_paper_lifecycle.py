"""Tests for paper trade lifecycle state machine."""
from __future__ import annotations

import pytest
from core.paper_trading.order_plan import OrderPlan, OrderSide, OrderStatus, ExitReason
from core.paper_trading.lifecycle import (
    LifecycleError, validate_transition, validate_close_requirements,
    transition_to_approval, transition_to_cancelled, transition_to_closed,
    is_terminal, is_paper_safe, VALID_TRANSITIONS, FORBIDDEN_STATUSES,
)


def _plan(status=OrderStatus.PLANNED_ONLY):
    return OrderPlan(
        plan_id="L-001", symbol="BTCUSDT", side=OrderSide.BUY,
        entry_price=50000, stop_loss=49000, take_profit=53000,
        invalidation_price=48500, risk_amount=100, position_size=0.1,
        status=status,
    )


class TestLifecycleTransitions:
    def test_planned_to_waiting(self):
        plan = _plan(OrderStatus.PLANNED_ONLY)
        result = transition_to_approval(plan)
        assert result.status == OrderStatus.WAITING_FOR_HUMAN_APPROVAL

    def test_planned_to_cancelled(self):
        plan = _plan(OrderStatus.PLANNED_ONLY)
        result = transition_to_cancelled(plan)
        assert result.status == OrderStatus.CANCELLED

    def test_waiting_to_cancelled(self):
        plan = _plan(OrderStatus.WAITING_FOR_HUMAN_APPROVAL)
        result = transition_to_cancelled(plan)
        assert result.status == OrderStatus.CANCELLED

    def test_waiting_to_closed(self):
        plan = _plan(OrderStatus.WAITING_FOR_HUMAN_APPROVAL)
        result = transition_to_closed(plan, ExitReason.TAKE_PROFIT, pnl=500)
        assert result.status == OrderStatus.SIMULATED_CLOSED
        assert result.exit_reason == ExitReason.TAKE_PROFIT
        assert result.closed_pnl == 500

    def test_closed_to_waiting_forbidden(self):
        plan = _plan(OrderStatus.SIMULATED_CLOSED)
        with pytest.raises(LifecycleError, match="Invalid transition"):
            transition_to_approval(plan)

    def test_closed_to_cancelled_forbidden(self):
        plan = _plan(OrderStatus.SIMULATED_CLOSED)
        with pytest.raises(LifecycleError, match="Invalid transition"):
            transition_to_cancelled(plan)

    def test_cancelled_to_waiting_forbidden(self):
        plan = _plan(OrderStatus.CANCELLED)
        with pytest.raises(LifecycleError, match="Invalid transition"):
            transition_to_approval(plan)

    def test_planned_to_closed_forbidden(self):
        """Cannot skip WAITING and go directly to CLOSED."""
        plan = _plan(OrderStatus.PLANNED_ONLY)
        with pytest.raises(LifecycleError, match="Invalid transition"):
            transition_to_closed(plan, ExitReason.STOP_LOSS, pnl=-100)


class TestCloseRequirements:
    def test_close_requires_exit_reason(self):
        plan = _plan(OrderStatus.WAITING_FOR_HUMAN_APPROVAL)
        with pytest.raises(LifecycleError, match="exit_reason required"):
            validate_close_requirements(plan, exit_reason=None)

    def test_close_with_exit_reason_ok(self):
        plan = _plan(OrderStatus.WAITING_FOR_HUMAN_APPROVAL)
        validate_close_requirements(plan, exit_reason=ExitReason.STOP_LOSS)


class TestForbiddenStatuses:
    def test_submitted_forbidden(self):
        assert not is_paper_safe("SUBMITTED")

    def test_live_forbidden(self):
        assert not is_paper_safe("LIVE")

    def test_testnet_forbidden(self):
        assert not is_paper_safe("TESTNET")

    def test_filled_forbidden(self):
        assert not is_paper_safe("FILLED")

    def test_paper_statuses_safe(self):
        for status in OrderStatus:
            assert is_paper_safe(status.value), f"{status.value} should be paper-safe"


class TestTerminalStatuses:
    def test_cancelled_is_terminal(self):
        assert is_terminal(OrderStatus.CANCELLED)

    def test_closed_is_terminal(self):
        assert is_terminal(OrderStatus.SIMULATED_CLOSED)

    def test_planned_not_terminal(self):
        assert not is_terminal(OrderStatus.PLANNED_ONLY)

    def test_waiting_not_terminal(self):
        assert not is_terminal(OrderStatus.WAITING_FOR_HUMAN_APPROVAL)


class TestTransitionTable:
    def test_all_transitions_documented(self):
        """Every OrderStatus should have an entry in VALID_TRANSITIONS."""
        for status in OrderStatus:
            assert status in VALID_TRANSITIONS, f"{status.value} missing from transition table"

    def test_terminal_no_outgoing(self):
        """Terminal statuses should have no outgoing transitions."""
        for status in (OrderStatus.CANCELLED, OrderStatus.SIMULATED_CLOSED):
            assert len(VALID_TRANSITIONS[status]) == 0
