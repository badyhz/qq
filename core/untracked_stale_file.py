from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UntrackedStaleFile:
    """Frozen record for a stale untracked file."""

    path: str
    days_stale: int
    last_modified_slot: str  # opaque slot identifier, no timestamp
    recommended_action: str  # e.g. "FLAG", "ESCALATE", "ARCHIVE"

    def is_escalated(self, threshold: int) -> bool:
        """Return True if days_stale exceeds threshold."""
        return self.days_stale >= threshold

    def stale_to_dict(self) -> dict:
        return {
            "path": self.path,
            "days_stale": self.days_stale,
            "last_modified_slot": self.last_modified_slot,
            "recommended_action": self.recommended_action,
        }
