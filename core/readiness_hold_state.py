from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HoldStateValue(Enum):
    CLEAR = "CLEAR"
    PENDING_REVIEW = "PENDING_REVIEW"
    BLOCKED = "BLOCKED"
    FROZEN = "FROZEN"


@dataclass(frozen=True)
class ReadinessHoldState:
    """Frozen hold state. No I/O, no timestamps."""

    state: HoldStateValue
    reason: str
    blocked_dimensions: tuple  # tuple of str
    exit_criteria: str
