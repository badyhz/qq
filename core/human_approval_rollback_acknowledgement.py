"""T1337 - Human approval rollback acknowledgement."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumanApprovalRollbackAcknowledgement:
    """Immutable record that a reviewer acknowledged a rollback scenario."""

    acknowledgement_id: str
    rollback_scenario: str
    acknowledged_by: str
    recovery_plan: str

    def to_dict(self) -> dict[str, object]:
        return {
            "acknowledgement_id": self.acknowledgement_id,
            "rollback_scenario": self.rollback_scenario,
            "acknowledged_by": self.acknowledged_by,
            "recovery_plan": self.recovery_plan,
        }

    def has_recovery_plan(self) -> bool:
        return len(self.recovery_plan.strip()) > 0
