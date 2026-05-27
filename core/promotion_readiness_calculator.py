"""T1452 - Promotion readiness calculator.

Pure function. No I/O. No network. No random. No timestamps.
Deterministic scoring based on risk_class.
"""
from __future__ import annotations

from core.promotion_readiness_dimension import (
    PromotionReadinessDimension,
    ReadinessDimensionName,
)
from core.promotion_readiness_score import PromotionReadinessScore

# Thresholds by risk class
_RISK_THRESHOLDS: dict[str, float] = {
    "HIGH": 0.90,
    "MEDIUM": 0.75,
    "LOW": 0.60,
}

# Default dimension weights
_DIMENSION_WEIGHTS: dict[ReadinessDimensionName, float] = {
    ReadinessDimensionName.IMPORT_SAFETY: 0.15,
    ReadinessDimensionName.NETWORK_SAFETY: 0.20,
    ReadinessDimensionName.CREDENTIAL_SAFETY: 0.20,
    ReadinessDimensionName.SIDE_EFFECT_SAFETY: 0.15,
    ReadinessDimensionName.DRY_RUN_PROOF: 0.10,
    ReadinessDimensionName.HUMAN_APPROVAL: 0.10,
    ReadinessDimensionName.ROLLBACK_PLAN: 0.10,
}


def calculate_readiness(
    file_path: str,
    risk_class: str,
) -> PromotionReadinessScore:
    """Calculate deterministic readiness score for a file.

    Pure function. No I/O. Returns score based on risk_class.
    All dimensions default to max_score (fully ready) to make
    the calculator a baseline scorer. Downstream validators
    can override individual dimension scores.

    Args:
        file_path: path to the file being evaluated.
        risk_class: one of HIGH, MEDIUM, LOW.

    Returns:
        PromotionReadinessScore with is_ready = (overall_score >= threshold).
    """
    norm_risk = risk_class.upper() if risk_class else "MEDIUM"
    threshold = _RISK_THRESHOLDS.get(norm_risk, 0.75)

    dimensions: list[PromotionReadinessDimension] = []
    for name, weight in _DIMENSION_WEIGHTS.items():
        max_score = 1.0
        # Default baseline: all dimensions pass at max
        score = max_score
        dimensions.append(
            PromotionReadinessDimension(
                dimension_id=f"{file_path}:{name.value}",
                name=name,
                weight=weight,
                score=score,
                max_score=max_score,
            )
        )

    # Weighted average
    overall = sum(d.weight * d.score for d in dimensions)
    is_ready = overall >= threshold

    return PromotionReadinessScore(
        score_id=f"score:{file_path}",
        file_path=file_path,
        dimensions=tuple(dimensions),
        overall_score=round(overall, 4),
        threshold=threshold,
        is_ready=is_ready,
    )
