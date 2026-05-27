from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumanReviewRejectionState:
    state: str
    gate_id: str
    rejector: str
    reason: str
    revision_allowed: bool


VALID_STATES: frozenset[str] = frozenset({
    "PENDING",
    "REJECTED",
    "REJECTED_PERMANENTLY",
    "REVISION_ALLOWED",
})


def build_rejection_state(
    gate_id: str,
    rejector: str = "",
    reason: str = "",
    revision_allowed: bool = False,
    state: str = "PENDING",
) -> HumanReviewRejectionState:
    if state not in VALID_STATES:
        raise ValueError(f"Invalid state: {state}. Must be one of {VALID_STATES}")
    return HumanReviewRejectionState(
        state=state,
        gate_id=gate_id,
        rejector=rejector,
        reason=reason,
        revision_allowed=revision_allowed,
    )
