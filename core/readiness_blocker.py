from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BlockerType(Enum):
    MISSING_TESTS = "MISSING_TESTS"
    MISSING_DOCS = "MISSING_DOCS"
    SAFETY_VIOLATION = "SAFETY_VIOLATION"
    UNRESOLVED_DEP = "UNRESOLVED_DEP"
    HIGH_RISK_UNMITIGATED = "HIGH_RISK_UNMITIGATED"


class BlockerSeverity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"


@dataclass(frozen=True)
class ReadinessBlocker:
    """Frozen blocker entry. No I/O, no timestamps."""

    blocker_id: str
    blocker_type: BlockerType
    severity: BlockerSeverity
    description: str
    resolution_path: str
