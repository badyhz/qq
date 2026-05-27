from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NoSubmitPlannerBoundary:
    component: str
    blocked: bool
    description: str


PLANNER_COMPONENTS: tuple[NoSubmitPlannerBoundary, ...] = (
    NoSubmitPlannerBoundary(
        component="planner_integration",
        blocked=True,
        description="Planner module must not be wired into execution path",
    ),
    NoSubmitPlannerBoundary(
        component="strategy_execution",
        blocked=True,
        description="Strategies must not execute live trades",
    ),
    NoSubmitPlannerBoundary(
        component="signal_to_order_pipeline",
        blocked=True,
        description="Signals must not flow through to order submission",
    ),
)
