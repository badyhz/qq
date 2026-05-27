"""T1373 - Frozen Backlog Action Policy."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrozenBacklogActionPolicy:
    """Immutable action policy.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    policy_id: str
    action_name: str
    allowed_for_risk: tuple[str, ...]
    requires_human_approval: bool
    blocked: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "action_name": self.action_name,
            "allowed_for_risk": self.allowed_for_risk,
            "requires_human_approval": self.requires_human_approval,
            "blocked": self.blocked,
        }


def build_action_policy(
    policy_id: str,
    action_name: str,
    allowed_for_risk: tuple[str, ...] = (),
    requires_human_approval: bool = False,
    blocked: bool = False,
) -> FrozenBacklogActionPolicy:
    """Factory for FrozenBacklogActionPolicy."""
    return FrozenBacklogActionPolicy(
        policy_id=policy_id,
        action_name=action_name,
        allowed_for_risk=allowed_for_risk,
        requires_human_approval=requires_human_approval,
        blocked=blocked,
    )
