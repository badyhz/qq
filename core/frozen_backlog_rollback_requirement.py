"""T1307 - Frozen Backlog Rollback Requirement."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrozenBacklogRollbackRequirement:
    """Immutable rollback requirement.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    requirement_id: str
    trigger_condition: str
    rollback_steps: tuple[str, ...]
    mandatory: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "requirement_id": self.requirement_id,
            "trigger_condition": self.trigger_condition,
            "rollback_steps": self.rollback_steps,
            "mandatory": self.mandatory,
        }


def build_rollback_requirement(
    requirement_id: str,
    trigger_condition: str,
    rollback_steps: tuple[str, ...] = (),
    mandatory: bool = True,
) -> FrozenBacklogRollbackRequirement:
    """Factory for FrozenBacklogRollbackRequirement."""
    return FrozenBacklogRollbackRequirement(
        requirement_id=requirement_id,
        trigger_condition=trigger_condition,
        rollback_steps=rollback_steps,
        mandatory=mandatory,
    )


def rollback_requirement_to_dict(
    r: FrozenBacklogRollbackRequirement,
) -> dict[str, object]:
    """Convert rollback requirement to a plain dict."""
    return r.to_dict()
