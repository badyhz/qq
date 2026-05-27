"""T1523 - Frozen Backlog Report Record."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrozenBacklogReportRecord:
    """Immutable report record for a single frozen backlog file.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    record_id: str
    file_path: str
    risk_class: str
    category: str
    allowed_actions: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    required_evidence: tuple[str, ...]
    readiness_score: float
    unlock_recommendation: str
    release_hold: str

    def to_dict(self) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "file_path": self.file_path,
            "risk_class": self.risk_class,
            "category": self.category,
            "allowed_actions": self.allowed_actions,
            "forbidden_actions": self.forbidden_actions,
            "required_evidence": self.required_evidence,
            "readiness_score": self.readiness_score,
            "unlock_recommendation": self.unlock_recommendation,
            "release_hold": self.release_hold,
        }
