"""T1371 - Frozen Backlog Decision Matrix."""
from __future__ import annotations

from dataclasses import dataclass

from core.frozen_backlog_decision_item import FrozenBacklogDecisionItem
from core.frozen_backlog_action_policy import FrozenBacklogActionPolicy
from core.frozen_backlog_matrix_verdict import FrozenBacklogMatrixVerdict


@dataclass(frozen=True)
class FrozenBacklogDecisionMatrix:
    """Immutable decision matrix.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    matrix_id: str
    items: tuple[FrozenBacklogDecisionItem, ...]
    policies: tuple[FrozenBacklogActionPolicy, ...]
    verdict: FrozenBacklogMatrixVerdict | None

    def to_dict(self) -> dict[str, object]:
        return {
            "matrix_id": self.matrix_id,
            "items": [i.to_dict() for i in self.items],
            "policies": [p.to_dict() for p in self.policies],
            "verdict": self.verdict.to_dict() if self.verdict else None,
        }


def build_decision_matrix(
    matrix_id: str,
    items: tuple[FrozenBacklogDecisionItem, ...] = (),
    policies: tuple[FrozenBacklogActionPolicy, ...] = (),
    verdict: FrozenBacklogMatrixVerdict | None = None,
) -> FrozenBacklogDecisionMatrix:
    """Factory for FrozenBacklogDecisionMatrix."""
    return FrozenBacklogDecisionMatrix(
        matrix_id=matrix_id,
        items=items,
        policies=policies,
        verdict=verdict,
    )
