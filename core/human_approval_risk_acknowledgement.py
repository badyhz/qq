"""T1336 - Human approval risk acknowledgement."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumanApprovalRiskAcknowledgement:
    """Immutable record that a reviewer acknowledged a specific risk."""

    acknowledgement_id: str
    risk_level: str
    acknowledged_by: str
    acknowledgement_text: str

    def to_dict(self) -> dict[str, object]:
        return {
            "acknowledgement_id": self.acknowledgement_id,
            "risk_level": self.risk_level,
            "acknowledged_by": self.acknowledged_by,
            "acknowledgement_text": self.acknowledgement_text,
        }

    def is_high_risk(self) -> bool:
        return self.risk_level.upper() in ("HIGH", "CRITICAL")
