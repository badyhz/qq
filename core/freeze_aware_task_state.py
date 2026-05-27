"""T1112 - Freeze-Aware Task State."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FreezeAwareTaskState:
    """Immutable task state enum-like.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    NOT_STARTED: str = "NOT_STARTED"
    IN_PROGRESS: str = "IN_PROGRESS"
    COMPLETED: str = "COMPLETED"
    HUMAN_REVIEW_REQUIRED: str = "HUMAN_REVIEW_REQUIRED"
    BLOCKED: str = "BLOCKED"
    PARTIAL: str = "PARTIAL"
    PASS: str = "PASS"
    DENIED: str = "DENIED"

    def validate_state(self, state: str) -> bool:
        """Return True if state is a known value."""
        known = (
            self.NOT_STARTED,
            self.IN_PROGRESS,
            self.COMPLETED,
            self.HUMAN_REVIEW_REQUIRED,
            self.BLOCKED,
            self.PARTIAL,
            self.PASS,
            self.DENIED,
        )
        return state in known
