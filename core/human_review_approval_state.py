from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumanReviewApprovalState:
    state: str
    gate_id: str
    approver: str
    timestamp_slot: str
    conditions: tuple[str, ...]


VALID_STATES: frozenset[str] = frozenset({
    "PENDING",
    "APPROVED",
    "APPROVED_WITH_CONDITIONS",
    "EXPIRED",
})


def build_approval_state(
    gate_id: str,
    approver: str = "",
    timestamp_slot: str = "",
    conditions: tuple[str, ...] = (),
    state: str = "PENDING",
) -> HumanReviewApprovalState:
    if state not in VALID_STATES:
        raise ValueError(f"Invalid state: {state}. Must be one of {VALID_STATES}")
    return HumanReviewApprovalState(
        state=state,
        gate_id=gate_id,
        approver=approver,
        timestamp_slot=timestamp_slot,
        conditions=tuple(conditions),
    )
