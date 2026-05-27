"""T1114 - Freeze-Aware Denial Reason."""
from __future__ import annotations

from dataclasses import dataclass

FREEZE_CONFLICT = "FREEZE_CONFLICT"
HIGH_RISK_TOUCH = "HIGH_RISK_TOUCH"
MISSING_DEP = "MISSING_DEP"
SAFETY_VIOLATION = "SAFETY_VIOLATION"

DENIAL_CATEGORIES = (
    FREEZE_CONFLICT,
    HIGH_RISK_TOUCH,
    MISSING_DEP,
    SAFETY_VIOLATION,
)


@dataclass(frozen=True)
class FreezeAwareDenialReason:
    """Immutable denial reason.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    reason_id: str
    category: str
    message: str
    related_task_id: str
    related_freeze_file: str
