from __future__ import annotations

from dataclasses import dataclass

from core.medium_risk_review import MediumRiskReview
from core.medium_risk_script_kind import MediumRiskScriptKind
from core.medium_risk_import_boundary import MediumRiskImportBoundary
from core.medium_risk_dry_run_requirement import MediumRiskDryRunRequirement
from core.medium_risk_command_safety import MediumRiskCommandSafety
from core.medium_risk_artifact_policy import MediumRiskArtifactPolicy
from core.medium_risk_commit_isolation import MediumRiskCommitIsolation
from core.medium_risk_promotion_checklist import MediumRiskPromotionChecklist
from core.medium_risk_review_verdict import MediumRiskReviewVerdict


@dataclass(frozen=True)
class MediumRiskModelCloseout:
    """T1220 - aggregates all medium-risk models."""

    model_count: int
    models: tuple[str, ...]
    verdict: str


def build_closeout() -> MediumRiskModelCloseout:
    """Build the closeout aggregating all medium-risk model names."""
    model_names = (
        "MediumRiskReview",
        "MediumRiskScriptKind",
        "MediumRiskImportBoundary",
        "MediumRiskDryRunRequirement",
        "MediumRiskCommandSafety",
        "MediumRiskArtifactPolicy",
        "MediumRiskCommitIsolation",
        "MediumRiskPromotionChecklist",
        "MediumRiskReviewVerdict",
        "MediumRiskModelCloseout",
    )
    return MediumRiskModelCloseout(
        model_count=len(model_names),
        models=tuple(model_names),
        verdict="PASS",
    )


def closeout_to_dict(c: MediumRiskModelCloseout) -> dict[str, object]:
    """Convert closeout to a plain dict (no I/O)."""
    return {
        "model_count": c.model_count,
        "models": list(c.models),
        "verdict": c.verdict,
    }
