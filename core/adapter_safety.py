"""Adapter safety boundary enforcement.

Prevents adapters from performing dangerous operations:
- No live trading
- No runtime trading integration
- No planner escalation
- No frozen writes
"""

from enum import Enum


class SafetyViolation(Exception):
    """Raised when an adapter request violates safety boundaries."""


class TaskCategory(Enum):
    SAFE_READONLY = "safe_readonly"
    SIMULATION = "simulation"
    GUARD_INJECTION = "guard_injection"
    HIGH_RISK_WRITE = "high_risk_write"
    LIVE_TRADING = "live_trading"
    RUNTIME_ORCHESTRATION = "runtime"


# Keyword hints per category for prompt-based classification
_CATEGORY_KEYWORDS: dict[TaskCategory, list[str]] = {
    TaskCategory.SAFE_READONLY: [
        "report", "analysis", "docs", "read", "list", "summary",
        "status", "check", "verify", "log",
    ],
    TaskCategory.SIMULATION: [
        "dry_run", "dry-run", "mock", "simulate", "shadow", "paper",
        "testnet",
    ],
    TaskCategory.GUARD_INJECTION: [
        "guard", "inject", "add_guard", "patch",
    ],
    TaskCategory.HIGH_RISK_WRITE: [
        "submit_order", "cancel_order", "place_order",
        "close_position", "open_position",
    ],
    TaskCategory.LIVE_TRADING: [
        "live", "real_order", "production",
    ],
    TaskCategory.RUNTIME_ORCHESTRATION: [
        "live_runner", "live_playbook", "orchestrate",
    ],
}


class AdapterSafetyBoundary:
    """Enforces which task categories adapters may execute."""

    def __init__(self) -> None:
        self._allowed_categories: set[TaskCategory] = {
            TaskCategory.SAFE_READONLY,
            TaskCategory.SIMULATION,
            TaskCategory.GUARD_INJECTION,
        }
        self._forbidden_patterns: list[str] = [
            "submit_order", "cancel_order", "place_order",
            "close_position", "open_position",
            "binance_api", "exchange_",
        ]
        self._frozen_patterns: list[str] = [
            "live_runner", "live_playbook",
            "submit_approved", "submit_replayed",
            "safe_flatten", "run_spot_testnet",
        ]

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def classify_task(self, task_id: str, prompt: str = "") -> TaskCategory:
        """Classify a task based on its ID and prompt content.

        Checks frozen patterns first, then prompt keywords, then task_id
        substring matching.
        """
        combined = f"{task_id} {prompt}".lower()

        # Frozen patterns always map to HIGH_RISK_WRITE
        if self.check_frozen_exclusion(task_id):
            return TaskCategory.HIGH_RISK_WRITE

        # Score each category by keyword hits in the combined text
        best_cat: TaskCategory | None = None
        best_score = 0
        for cat, keywords in _CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > best_score:
                best_score = score
                best_cat = cat

        if best_cat is not None and best_score > 0:
            return best_cat

        # Default: treat unknown tasks as safe readonly
        return TaskCategory.SAFE_READONLY

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_request(
        self,
        task_id: str,
        prompt: str = "",
        adapter_id: str = "",
    ) -> dict:
        """Validate an adapter request. Raises SafetyViolation if forbidden.

        Returns a dict with validation details on success.
        """
        combined = f"{task_id} {prompt} {adapter_id}".lower()

        # Check frozen exclusion first
        if self.check_frozen_exclusion(task_id):
            raise SafetyViolation(
                f"Task '{task_id}' matches frozen pattern — blocked"
            )

        # Check forbidden content patterns
        for pattern in self._forbidden_patterns:
            if pattern in combined:
                raise SafetyViolation(
                    f"Forbidden pattern '{pattern}' detected in request"
                )

        # Classify and verify category is allowed
        category = self.classify_task(task_id, prompt)
        if not self.is_allowed(category):
            raise SafetyViolation(
                f"Category '{category.value}' is not in allowed set"
            )

        return {
            "task_id": task_id,
            "adapter_id": adapter_id,
            "category": category.value,
            "allowed": True,
        }

    # ------------------------------------------------------------------
    # Allowed-set management
    # ------------------------------------------------------------------

    def is_allowed(self, category: TaskCategory) -> bool:
        """Check if category is in allowed set."""
        return category in self._allowed_categories

    def add_allowed(self, category: TaskCategory) -> None:
        """Add category to allowed set."""
        self._allowed_categories.add(category)

    def remove_allowed(self, category: TaskCategory) -> None:
        """Remove category from allowed set."""
        self._allowed_categories.discard(category)

    # ------------------------------------------------------------------
    # Frozen exclusion
    # ------------------------------------------------------------------

    def check_frozen_exclusion(self, task_id: str) -> bool:
        """Return True if task matches frozen patterns (should be blocked)."""
        tid = task_id.lower()
        return any(fp in tid for fp in self._frozen_patterns)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        """Safety boundary stats."""
        return {
            "allowed_categories": sorted(c.value for c in self._allowed_categories),
            "forbidden_patterns": list(self._forbidden_patterns),
            "frozen_patterns": list(self._frozen_patterns),
        }
