"""T1462 - HoldDecisionReport frozen dataclass."""
from __future__ import annotations

from dataclasses import dataclass


def _validate_hold_status(value: str) -> None:
    if value != "HOLD":
        raise ValueError(
            f"HoldDecisionReport.current_hold_status must be HOLD, got: {value!r}"
        )


@dataclass(frozen=True)
class HoldDecisionReport:
    report_id: str
    file_path: str
    risk_class: str
    current_hold_status: str
    readiness_score: float
    unlock_recommendation: str
    human_decision: str
    decision_rationale: str
    required_evidence: tuple[str, ...]

    HOLD: str = "HOLD"
    PENDING: str = "PENDING"
    APPROVED: str = "APPROVED"
    DENIED: str = "DENIED"
    ALL_DECISIONS: tuple[str, ...] = ("PENDING", "APPROVED", "DENIED")

    def __post_init__(self) -> None:
        _validate_hold_status(self.current_hold_status)
