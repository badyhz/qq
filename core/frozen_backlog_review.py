"""T1301 - Frozen Backlog Review."""
from __future__ import annotations

from dataclasses import dataclass

from core.frozen_backlog_review_state import FrozenBacklogReviewState
from core.frozen_backlog_review_verdict import FrozenBacklogReviewVerdict


@dataclass(frozen=True)
class FrozenBacklogReview:
    """Immutable backlog review.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    review_id: str
    backlog_items: tuple[str, ...]
    review_state: FrozenBacklogReviewState
    verdict: FrozenBacklogReviewVerdict | None

    def to_dict(self) -> dict[str, object]:
        return {
            "review_id": self.review_id,
            "backlog_items": self.backlog_items,
            "review_state": self.review_state.to_dict(),
            "verdict": self.verdict.to_dict() if self.verdict else None,
        }


def build_review(
    review_id: str,
    backlog_items: tuple[str, ...] = (),
    review_state: FrozenBacklogReviewState | None = None,
    verdict: FrozenBacklogReviewVerdict | None = None,
) -> FrozenBacklogReview:
    """Factory for FrozenBacklogReview."""
    from core.frozen_backlog_review_state import PENDING, build_state

    if review_state is None:
        review_state = build_state(PENDING)
    return FrozenBacklogReview(
        review_id=review_id,
        backlog_items=backlog_items,
        review_state=review_state,
        verdict=verdict,
    )


def review_to_dict(r: FrozenBacklogReview) -> dict[str, object]:
    """Convert review to a plain dict."""
    return r.to_dict()
