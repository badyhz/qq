from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UntrackedFreezeEvidence:
    """Frozen evidence record for an untracked file state transition."""

    evidence_id: str
    file_path: str
    classification_record: bool
    risk_assessment: bool
    human_approval: bool
    safety_check: bool

    def is_fully_evidenced(self) -> bool:
        """Return True if all evidence fields are present."""
        return (
            self.classification_record
            and self.risk_assessment
            and self.human_approval
            and self.safety_check
        )

    def has_classification(self) -> bool:
        return self.classification_record

    def has_risk_assessment(self) -> bool:
        return self.risk_assessment

    def has_human_approval(self) -> bool:
        return self.human_approval

    def has_safety_check(self) -> bool:
        return self.safety_check

    def evidence_to_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "file_path": self.file_path,
            "classification_record": self.classification_record,
            "risk_assessment": self.risk_assessment,
            "human_approval": self.human_approval,
            "safety_check": self.safety_check,
        }
