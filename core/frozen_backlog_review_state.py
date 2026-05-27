"""T1303 - Frozen Backlog Review State."""
from __future__ import annotations

from dataclasses import dataclass


PENDING = "PENDING"
IN_REVIEW = "IN_REVIEW"
APPROVED = "APPROVED"
DENIED = "DENIED"
ESCALATED = "ESCALATED"

ALL_STATES: tuple[str, ...] = (
    PENDING,
    IN_REVIEW,
    APPROVED,
    DENIED,
    ESCALATED,
)


@dataclass(frozen=True)
class FrozenBacklogReviewState:
    """Immutable review state.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    state: str

    def __post_init__(self) -> None:
        if self.state not in ALL_STATES:
            raise ValueError(
                f"Invalid state {self.state!r}; must be one of {ALL_STATES}"
            )


def build_state(state: str) -> FrozenBacklogReviewState:
    """Factory for FrozenBacklogReviewState."""
    return FrozenBacklogReviewState(state=state)


def state_to_dict(s: FrozenBacklogReviewState) -> dict[str, str]:
    """Convert state to a plain dict."""
    return {"state": s.state}
