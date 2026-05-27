from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DirtyWorkspaceModelCloseout:
    model_count: int
    models: tuple[str, ...]
    verdict: str

    def to_dict(self) -> dict[str, object]:
        return {
            "model_count": self.model_count,
            "models": self.models,
            "verdict": self.verdict,
        }


_ALL_MODELS: tuple[str, ...] = (
    "dirty_workspace_governance",
    "dirty_workspace_file_category",
    "dirty_workspace_risk_level",
    "dirty_workspace_action_recommendation",
    "dirty_workspace_file_record",
    "dirty_workspace_classification_result",
    "dirty_workspace_freeze_violation",
    "dirty_workspace_duplicate_record",
    "dirty_workspace_governance_verdict",
    "dirty_workspace_model_closeout",
)


def build_closeout() -> DirtyWorkspaceModelCloseout:
    return DirtyWorkspaceModelCloseout(
        model_count=len(_ALL_MODELS),
        models=_ALL_MODELS,
        verdict="PASS",
    )


def closeout_to_dict(c: DirtyWorkspaceModelCloseout) -> dict[str, object]:
    return c.to_dict()
