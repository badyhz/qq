"""Quant Workflow Policy — quant-specific safety rules.

Separate layer from workflow_safety. Enforces quant-safe categories
and blocks destructive trading actions.
"""
from __future__ import annotations

from dataclasses import dataclass, field


BLOCKED_ACTIONS: set[str] = {
    "submit",
    "cancel",
    "flatten",
    "live_execution",
    "planner_escalation",
    "place_order",
    "close_position",
}

ALLOWED_CATEGORIES: set[str] = {
    "READONLY",
    "AUDIT",
    "DOCS",
    "SIMULATION",
    "CLOSEOUT",
}


@dataclass
class QuantPolicyViolation:
    rule: str
    severity: str
    detail: str
    task_id: str | None = None


@dataclass
class QuantWorkflowPolicy:
    blocked_actions: set[str] = field(default_factory=lambda: BLOCKED_ACTIONS.copy())
    allowed_categories: set[str] = field(default_factory=lambda: ALLOWED_CATEGORIES.copy())

    def is_allowed(self, category: str) -> bool:
        """Check if a task category is permitted."""
        return category in self.allowed_categories

    def validate_task(self, task_id: str, category: str) -> list[QuantPolicyViolation]:
        """Validate a single task against policy rules."""
        violations: list[QuantPolicyViolation] = []

        if not self.is_allowed(category):
            violations.append(
                QuantPolicyViolation(
                    rule="BLOCKED_CATEGORY",
                    severity="CRITICAL",
                    detail=f"Category '{category}' is not in allowed set",
                    task_id=task_id,
                )
            )

        if category in self.blocked_actions:
            violations.append(
                QuantPolicyViolation(
                    rule="BLOCKED_ACTION",
                    severity="CRITICAL",
                    detail=f"Action '{category}' is a blocked action",
                    task_id=task_id,
                )
            )

        return violations

    def validate_workflow_policy(self, tasks: list[dict]) -> list[QuantPolicyViolation]:
        """Validate all tasks in a workflow."""
        violations: list[QuantPolicyViolation] = []
        for task in tasks:
            task_id = task.get("id", "")
            category = task.get("category", "")
            violations.extend(self.validate_task(task_id, category))
        return violations

    def summary(self) -> dict:
        """Return policy state."""
        return {
            "blocked_actions": sorted(self.blocked_actions),
            "allowed_categories": sorted(self.allowed_categories),
            "blocked_count": len(self.blocked_actions),
            "allowed_count": len(self.allowed_categories),
        }


def validate_quant_safety(workflow_data: dict) -> dict:
    """Quick validation function for quant workflow safety."""
    policy = QuantWorkflowPolicy()
    tasks = workflow_data.get("tasks", [])
    violations = policy.validate_workflow_policy(tasks)
    return {
        "safe": len(violations) == 0,
        "violations": [
            {"rule": v.rule, "severity": v.severity, "detail": v.detail, "task_id": v.task_id}
            for v in violations
        ],
        "summary": policy.summary(),
    }
