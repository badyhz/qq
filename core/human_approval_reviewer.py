"""T1333 - Human approval reviewer identity."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumanApprovalReviewer:
    """Immutable representation of an approval reviewer."""

    reviewer_id: str
    name: str
    role: str
    authority_level: int

    def to_dict(self) -> dict[str, object]:
        return {
            "reviewer_id": self.reviewer_id,
            "name": self.name,
            "role": self.role,
            "authority_level": self.authority_level,
        }

    def can_approve(self, required_level: int) -> bool:
        """Return True when reviewer authority meets the required threshold."""
        return self.authority_level >= required_level
