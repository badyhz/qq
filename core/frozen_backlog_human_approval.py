"""T1308 - Frozen Backlog Human Approval."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrozenBacklogHumanApproval:
    """Immutable human approval record.

    Pure deterministic. No I/O. No network.
    """

    approval_id: str
    reviewer: str
    timestamp_iso: str
    decision: str
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "approval_id": self.approval_id,
            "reviewer": self.reviewer,
            "timestamp_iso": self.timestamp_iso,
            "decision": self.decision,
            "evidence_refs": self.evidence_refs,
        }


def build_human_approval(
    approval_id: str,
    reviewer: str,
    timestamp_iso: str,
    decision: str,
    evidence_refs: tuple[str, ...] = (),
) -> FrozenBacklogHumanApproval:
    """Factory for FrozenBacklogHumanApproval."""
    return FrozenBacklogHumanApproval(
        approval_id=approval_id,
        reviewer=reviewer,
        timestamp_iso=timestamp_iso,
        decision=decision,
        evidence_refs=evidence_refs,
    )


def human_approval_to_dict(
    a: FrozenBacklogHumanApproval,
) -> dict[str, object]:
    """Convert human approval to a plain dict."""
    return a.to_dict()
