"""T1376 - Frozen Backlog Promotion Gate."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrozenBacklogPromotionGate:
    """Immutable promotion gate.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    gate_id: str
    from_state: str
    to_state: str
    prerequisites: tuple[str, ...]
    blockers: tuple[str, ...]
    requires_human: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "gate_id": self.gate_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "prerequisites": self.prerequisites,
            "blockers": self.blockers,
            "requires_human": self.requires_human,
        }


def build_promotion_gate(
    gate_id: str,
    from_state: str,
    to_state: str,
    prerequisites: tuple[str, ...] = (),
    blockers: tuple[str, ...] = (),
    requires_human: bool = False,
) -> FrozenBacklogPromotionGate:
    """Factory for FrozenBacklogPromotionGate."""
    return FrozenBacklogPromotionGate(
        gate_id=gate_id,
        from_state=from_state,
        to_state=to_state,
        prerequisites=prerequisites,
        blockers=blockers,
        requires_human=requires_human,
    )
