"""Schedule-Time Safety Gate — validates tasks BEFORE dispatcher runs them.

Operates at dispatch time, not load time. Complements workflow_safety.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_BLOCKED_CATEGORIES = {
    "submit",
    "cancel",
    "flatten",
    "live_execution",
    "planner_escalation",
    "place_order",
    "close_position",
}

DEFAULT_BLOCKED_TASK_PATTERNS = [
    "live_runner",
    "submit_order",
    "cancel_order",
    "flatten_position",
]


@dataclass
class ScheduleViolation:
    rule: str
    severity: str
    detail: str
    task_id: str | None = None


@dataclass
class ScheduleValidationResult:
    allowed: bool
    violations: list[ScheduleViolation] = field(default_factory=list)
    blocked_tasks: list[str] = field(default_factory=list)
    passed_tasks: list[str] = field(default_factory=list)


class ScheduleSafetyGate:
    def __init__(self) -> None:
        self._blocked_categories: set[str] = set(DEFAULT_BLOCKED_CATEGORIES)
        self._blocked_patterns: list[str] = list(DEFAULT_BLOCKED_TASK_PATTERNS)
        self._stats = {"total_checked": 0, "total_blocked": 0, "total_passed": 0}

    # ── core validation ──────────────────────────────────────────────

    def validate_dispatch(
        self,
        task_id: str,
        task_category: str,
        task_deps: list[str] | None = None,
    ) -> ScheduleValidationResult:
        violations: list[ScheduleViolation] = []

        # 1. category check
        if task_category in self._blocked_categories:
            violations.append(
                ScheduleViolation(
                    rule="BLOCKED_CATEGORY",
                    severity="CRITICAL",
                    detail=f"Category '{task_category}' is blocked at schedule time",
                    task_id=task_id,
                )
            )

        # 2. task_id pattern check
        tid_lower = task_id.lower()
        for pattern in self._blocked_patterns:
            if pattern in tid_lower:
                violations.append(
                    ScheduleViolation(
                        rule="BLOCKED_TASK_PATTERN",
                        severity="CRITICAL",
                        detail=f"Task '{task_id}' matches blocked pattern '{pattern}'",
                        task_id=task_id,
                    )
                )

        allowed = len(violations) == 0

        self._stats["total_checked"] += 1
        if allowed:
            self._stats["total_passed"] += 1
        else:
            self._stats["total_blocked"] += 1

        return ScheduleValidationResult(
            allowed=allowed,
            violations=violations,
            blocked_tasks=[] if allowed else [task_id],
            passed_tasks=[task_id] if allowed else [],
        )

    def validate_batch(self, tasks: list[dict]) -> ScheduleValidationResult:
        all_violations: list[ScheduleViolation] = []
        blocked: list[str] = []
        passed: list[str] = []

        for t in tasks:
            result = self.validate_dispatch(
                task_id=t.get("task_id", ""),
                task_category=t.get("category", ""),
                task_deps=t.get("deps"),
            )
            all_violations.extend(result.violations)
            blocked.extend(result.blocked_tasks)
            passed.extend(result.passed_tasks)

        return ScheduleValidationResult(
            allowed=len(blocked) == 0,
            violations=all_violations,
            blocked_tasks=blocked,
            passed_tasks=passed,
        )

    def is_dispatchable(self, task_id: str, task_category: str) -> bool:
        result = self.validate_dispatch(task_id, task_category)
        return result.allowed

    # ── configuration ────────────────────────────────────────────────

    def add_blocked_category(self, category: str) -> None:
        self._blocked_categories.add(category)

    def remove_blocked_category(self, category: str) -> None:
        self._blocked_categories.discard(category)

    # ── stats ────────────────────────────────────────────────────────

    def summary(self) -> dict:
        return {
            "total_checked": self._stats["total_checked"],
            "total_blocked": self._stats["total_blocked"],
            "total_passed": self._stats["total_passed"],
            "blocked_categories": sorted(self._blocked_categories),
            "blocked_patterns": list(self._blocked_patterns),
        }
