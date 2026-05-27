from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumanReviewRollbackRequirement:
    gate_id: str
    rollback_steps: tuple[str, ...]
    verification_command: str
    expected_outcome: str


def build_rollback_requirement(
    gate_id: str,
    rollback_steps: tuple[str, ...] = (),
    verification_command: str = "",
    expected_outcome: str = "",
) -> HumanReviewRollbackRequirement:
    return HumanReviewRollbackRequirement(
        gate_id=gate_id,
        rollback_steps=tuple(rollback_steps),
        verification_command=verification_command,
        expected_outcome=expected_outcome,
    )
