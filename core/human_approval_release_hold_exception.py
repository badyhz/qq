"""T1339 - Human approval release-hold exception."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumanApprovalReleaseHoldException:
    """Immutable record of an approved exception to a release hold.

    release_hold = HOLD by default.  This model captures the rare case
    where an exception is granted; it does NOT lift the hold itself.
    """

    exception_id: str
    original_hold: str
    exception_reason: str
    approved_by: str
    expiry_iso: str

    def to_dict(self) -> dict[str, object]:
        return {
            "exception_id": self.exception_id,
            "original_hold": self.original_hold,
            "exception_reason": self.exception_reason,
            "approved_by": self.approved_by,
            "expiry_iso": self.expiry_iso,
        }

    def is_hold(self) -> bool:
        return self.original_hold.upper() == "HOLD"
