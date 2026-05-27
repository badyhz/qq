"""Release hold dashboard — frozen dataclass for governance status.

T1397 — Pure, frozen, no I/O, no network, no random, no timestamps, no env reads.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ReleaseHoldDashboard:
    """Dashboard showing the current release hold status."""

    dashboard_id: str
    hold_status: str  # always HOLD
    frozen_count: int
    medium_count: int
    governance_layers: Tuple[str, ...]
    next_human_action: str
