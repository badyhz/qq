"""Paper trade lifecycle state machine — local simulation only."""
from __future__ import annotations

from typing import Optional

from core.paper_trading.order_plan import OrderPlan, OrderStatus, ExitReason


# Valid transitions: (from_status, to_status)
VALID_TRANSITIONS = {
    OrderStatus.PLANNED_ONLY: {OrderStatus.WAITING_FOR_HUMAN_APPROVAL, OrderStatus.CANCELLED},
    OrderStatus.WAITING_FOR_HUMAN_APPROVAL: {OrderStatus.CANCELLED, OrderStatus.SIMULATED_CLOSED},
    OrderStatus.CANCELLED: set(),
    OrderStatus.SIMULATED_CLOSED: set(),
}

# Forbidden statuses — never allowed in paper trading
FORBIDDEN_STATUSES = {"SUBMITTED", "LIVE", "TESTNET", "FILLED", "PARTIALLY_FILLED"}


class LifecycleError(Exception):
    """Raised when a lifecycle transition is invalid."""
    pass


def validate_transition(current: OrderStatus, target: OrderStatus) -> None:
    """Validate that a status transition is allowed."""
    current_val = current if isinstance(current, OrderStatus) else OrderStatus(current)
    target_val = target if isinstance(target, OrderStatus) else OrderStatus(target)

    allowed = VALID_TRANSITIONS.get(current_val, set())
    if target_val not in allowed:
        raise LifecycleError(
            f"Invalid transition: {current_val.value} → {target_val.value}"
        )


def validate_close_requirements(plan: OrderPlan, exit_reason: Optional[ExitReason] = None) -> None:
    """Validate requirements for closing a plan."""
    if exit_reason is None:
        raise LifecycleError("exit_reason required for SIMULATED_CLOSED")


def transition_to_approval(plan: OrderPlan) -> OrderPlan:
    """Transition plan to WAITING_FOR_HUMAN_APPROVAL."""
    validate_transition(plan.status, OrderStatus.WAITING_FOR_HUMAN_APPROVAL)
    return plan.with_status(OrderStatus.WAITING_FOR_HUMAN_APPROVAL)


def transition_to_cancelled(plan: OrderPlan) -> OrderPlan:
    """Transition plan to CANCELLED."""
    validate_transition(plan.status, OrderStatus.CANCELLED)
    return plan.with_status(OrderStatus.CANCELLED)


def transition_to_closed(
    plan: OrderPlan,
    exit_reason: ExitReason,
    pnl: float = 0.0,
) -> OrderPlan:
    """Transition plan to SIMULATED_CLOSED."""
    validate_transition(plan.status, OrderStatus.SIMULATED_CLOSED)
    validate_close_requirements(plan, exit_reason)
    return plan.with_status(OrderStatus.SIMULATED_CLOSED, exit_reason, pnl)


def is_terminal(status: OrderStatus) -> bool:
    """Check if a status is terminal (no further transitions)."""
    return status in (OrderStatus.CANCELLED, OrderStatus.SIMULATED_CLOSED)


def is_paper_safe(status_str: str) -> bool:
    """Check if a status string is safe for paper trading."""
    return status_str.upper() not in FORBIDDEN_STATUSES
