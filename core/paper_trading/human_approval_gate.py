"""Human approval gate — only allows WAITING_FOR_HUMAN_APPROVAL status."""
from __future__ import annotations
from typing import Dict, Any

from core.paper_trading.order_plan import OrderPlan, OrderStatus


class HumanApprovalGate:
    """Gate that transitions plans to WAITING_FOR_HUMAN_APPROVAL.

    This gate never auto-approves. It only sets the status to indicate
    that a human must review before any action is taken.
    """

    def submit_for_approval(self, plan: OrderPlan) -> OrderPlan:
        """Submit a plan for human approval.

        Only PLANNED_ONLY plans can be submitted.
        Returns a new plan with WAITING_FOR_HUMAN_APPROVAL status.
        """
        if plan.status != OrderStatus.PLANNED_ONLY:
            raise ValueError(
                f"Cannot submit plan in {plan.status.value} status. "
                f"Only PLANNED_ONLY plans can be submitted."
            )

        if plan.position_size <= 0:
            raise ValueError("Cannot submit plan with zero position size")

        return plan.with_status(OrderStatus.WAITING_FOR_HUMAN_APPROVAL)

    def approve(self, plan: OrderPlan) -> OrderPlan:
        """Human approves the plan (paper simulation only).

        In paper mode, approval just confirms the plan is ready for simulation.
        No real order is placed.
        """
        if plan.status != OrderStatus.WAITING_FOR_HUMAN_APPROVAL:
            raise ValueError(
                f"Cannot approve plan in {plan.status.value} status. "
                f"Must be WAITING_FOR_HUMAN_APPROVAL."
            )
        # In paper mode, "approval" just keeps it in WAITING status
        # The plan stays WAITING_FOR_HUMAN_APPROVAL until simulated
        return plan

    def cancel(self, plan: OrderPlan) -> OrderPlan:
        """Human cancels the plan."""
        if plan.status in (OrderStatus.CANCELLED, OrderStatus.SIMULATED_CLOSED):
            raise ValueError(f"Plan already in {plan.status.value} status")
        return plan.with_status(OrderStatus.CANCELLED)

    def get_pending_plans(self, plans: list[OrderPlan]) -> list[OrderPlan]:
        """Get all plans waiting for human approval."""
        return [p for p in plans if p.status == OrderStatus.WAITING_FOR_HUMAN_APPROVAL]

    def gate_summary(self, plans: list[OrderPlan]) -> Dict[str, Any]:
        """Summary of gate status."""
        statuses = {}
        for p in plans:
            statuses[p.status.value] = statuses.get(p.status.value, 0) + 1
        return {
            "total": len(plans),
            "statuses": statuses,
            "pending_approval": statuses.get("WAITING_FOR_HUMAN_APPROVAL", 0),
        }
