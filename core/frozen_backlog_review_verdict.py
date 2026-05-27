"""T1309 - Frozen Backlog Review Verdict."""
from __future__ import annotations

from dataclasses import dataclass

from core.frozen_backlog_denial_reason import FrozenBacklogDenialReason
from core.frozen_backlog_human_approval import FrozenBacklogHumanApproval

VALID_VERDICTS: tuple[str, ...] = ("HOLD", "APPROVED", "DENIED", "ESCALATED")


@dataclass(frozen=True)
class FrozenBacklogReviewVerdict:
    """Immutable review verdict.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    verdict: str
    notes: str
    denial_reasons: tuple[FrozenBacklogDenialReason, ...]
    approvals: tuple[FrozenBacklogHumanApproval, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict,
            "notes": self.notes,
            "denial_reasons": [r.to_dict() for r in self.denial_reasons],
            "approvals": [a.to_dict() for a in self.approvals],
        }


def build_verdict(
    verdict: str,
    notes: str = "",
    denial_reasons: tuple[FrozenBacklogDenialReason, ...] = (),
    approvals: tuple[FrozenBacklogHumanApproval, ...] = (),
) -> FrozenBacklogReviewVerdict:
    """Factory with validation for FrozenBacklogReviewVerdict."""
    if verdict not in VALID_VERDICTS:
        raise ValueError(
            f"Invalid verdict {verdict!r}; must be one of {VALID_VERDICTS}"
        )
    return FrozenBacklogReviewVerdict(
        verdict=verdict,
        notes=notes,
        denial_reasons=denial_reasons,
        approvals=approvals,
    )


def verdict_to_dict(v: FrozenBacklogReviewVerdict) -> dict[str, object]:
    """Convert verdict to a plain dict."""
    return v.to_dict()
