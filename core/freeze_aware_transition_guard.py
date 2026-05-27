"""T1118 - Freeze-Aware Transition Guard."""
from __future__ import annotations

from dataclasses import dataclass

TRANSITIONS = (
    ("NOT_STARTED", "IN_PROGRESS", "admission_passed", False),
    ("NOT_STARTED", "DENIED", "admission_failed", False),
    ("NOT_STARTED", "BLOCKED", "dependency_or_freeze_block", False),
    ("IN_PROGRESS", "COMPLETED", "all_criteria_met", False),
    ("IN_PROGRESS", "PARTIAL", "some_criteria_met", False),
    ("IN_PROGRESS", "BLOCKED", "new_block_detected", False),
    ("IN_PROGRESS", "HUMAN_REVIEW_REQUIRED", "review_triggered", False),
    ("IN_PROGRESS", "DENIED", "safety_violation", True),
    ("COMPLETED", "PASS", "verification_passed", False),
    ("COMPLETED", "HUMAN_REVIEW_REQUIRED", "review_triggered", True),
    ("HUMAN_REVIEW_REQUIRED", "IN_PROGRESS", "human_approved", True),
    ("HUMAN_REVIEW_REQUIRED", "DENIED", "human_rejected", True),
    ("HUMAN_REVIEW_REQUIRED", "PARTIAL", "human_requested_changes", True),
    ("BLOCKED", "NOT_STARTED", "block_resolved", False),
    ("PARTIAL", "COMPLETED", "remaining_criteria_met", False),
    ("PARTIAL", "DENIED", "human_abandoned", True),
    ("PARTIAL", "BLOCKED", "new_block_detected", False),
    ("PASS", "PASS", "no_op", False),
)


@dataclass(frozen=True)
class FreezeAwareTransitionGuard:
    """Immutable transition guard.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    from_state: str
    to_state: str
    guard_condition: str
    requires_human_approval: bool


def validate_transition(from_state: str, to_state: str) -> bool:
    """Return True if the transition is allowed."""
    for t in TRANSITIONS:
        if t[0] == from_state and t[1] == to_state:
            return True
    return False
