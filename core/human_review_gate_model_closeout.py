from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumanReviewGateModelCloseout:
    model_count: int
    models: tuple[str, ...]
    verdict: str


EXPECTED_MODELS: tuple[str, ...] = (
    "human_review_gate",
    "human_review_decision",
    "human_review_approval_state",
    "human_review_rejection_state",
    "human_review_escalation_rule",
    "human_review_evidence_checklist",
    "human_review_forbidden_approval",
    "human_review_rollback_requirement",
    "human_review_gate_verdict",
    "human_review_gate_model_closeout",
)


def build_closeout(
    models: tuple[str, ...] = EXPECTED_MODELS,
    verdict: str = "PASS",
) -> HumanReviewGateModelCloseout:
    return HumanReviewGateModelCloseout(
        model_count=len(models),
        models=tuple(models),
        verdict=verdict,
    )


def closeout_to_dict(c: HumanReviewGateModelCloseout) -> dict[str, object]:
    return {
        "model_count": c.model_count,
        "models": list(c.models),
        "verdict": c.verdict,
    }
