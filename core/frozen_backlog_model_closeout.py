"""T1310 - Frozen Backlog Model Closeout."""
from __future__ import annotations

from dataclasses import dataclass

_ALL_MODELS: tuple[str, ...] = (
    "frozen_backlog_item_kind",
    "frozen_backlog_review_state",
    "frozen_backlog_denial_reason",
    "frozen_backlog_evidence_requirement",
    "frozen_backlog_promotion_boundary",
    "frozen_backlog_rollback_requirement",
    "frozen_backlog_human_approval",
    "frozen_backlog_review_verdict",
    "frozen_backlog_review",
    "frozen_backlog_model_closeout",
)


@dataclass(frozen=True)
class FrozenBacklogModelCloseout:
    """Immutable model closeout.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    closeout_id: str
    task_range: str
    models_created: tuple[str, ...]
    verdict: str

    def to_dict(self) -> dict[str, object]:
        return {
            "closeout_id": self.closeout_id,
            "task_range": self.task_range,
            "models_created": self.models_created,
            "verdict": self.verdict,
        }


def build_closeout(
    closeout_id: str = "T1301-T1310",
    task_range: str = "T1301-T1310",
) -> FrozenBacklogModelCloseout:
    """Factory for FrozenBacklogModelCloseout."""
    return FrozenBacklogModelCloseout(
        closeout_id=closeout_id,
        task_range=task_range,
        models_created=_ALL_MODELS,
        verdict="HOLD",
    )


def closeout_to_dict(c: FrozenBacklogModelCloseout) -> dict[str, object]:
    """Convert closeout to a plain dict."""
    return c.to_dict()
