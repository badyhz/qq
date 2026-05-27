"""T1306 - Frozen Backlog Promotion Boundary."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrozenBacklogPromotionBoundary:
    """Immutable promotion boundary.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    boundary_id: str
    from_state: str
    to_state: str
    requires_human_approval: bool
    blocked: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "boundary_id": self.boundary_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "requires_human_approval": self.requires_human_approval,
            "blocked": self.blocked,
        }


def build_promotion_boundary(
    boundary_id: str,
    from_state: str,
    to_state: str,
    requires_human_approval: bool = True,
    blocked: bool = False,
) -> FrozenBacklogPromotionBoundary:
    """Factory for FrozenBacklogPromotionBoundary."""
    return FrozenBacklogPromotionBoundary(
        boundary_id=boundary_id,
        from_state=from_state,
        to_state=to_state,
        requires_human_approval=requires_human_approval,
        blocked=blocked,
    )


def promotion_boundary_to_dict(
    b: FrozenBacklogPromotionBoundary,
) -> dict[str, object]:
    """Convert promotion boundary to a plain dict."""
    return b.to_dict()
