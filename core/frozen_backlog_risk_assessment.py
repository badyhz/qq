"""T1375 - Frozen Backlog Risk Assessment."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrozenBacklogRiskAssessment:
    """Immutable risk assessment.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    assessment_id: str
    file_path: str
    risk_factors: tuple[str, ...]
    risk_score: float
    mitigation_steps: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "assessment_id": self.assessment_id,
            "file_path": self.file_path,
            "risk_factors": self.risk_factors,
            "risk_score": self.risk_score,
            "mitigation_steps": self.mitigation_steps,
        }


def build_risk_assessment(
    assessment_id: str,
    file_path: str,
    risk_factors: tuple[str, ...] = (),
    risk_score: float = 0.0,
    mitigation_steps: tuple[str, ...] = (),
) -> FrozenBacklogRiskAssessment:
    """Factory for FrozenBacklogRiskAssessment."""
    return FrozenBacklogRiskAssessment(
        assessment_id=assessment_id,
        file_path=file_path,
        risk_factors=risk_factors,
        risk_score=risk_score,
        mitigation_steps=mitigation_steps,
    )
