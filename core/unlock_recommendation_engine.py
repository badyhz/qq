"""T1460 - Pure unlock recommendation engine."""
from __future__ import annotations

from core.unlock_recommendation import UnlockRecommendation


def generate_unlock_recommendation(
    *,
    file_path: str,
    risk_class: str,
    readiness_score: float,
) -> UnlockRecommendation:
    """Deterministic unlock recommendation. Pure, no I/O."""
    risk = str(risk_class or "").strip().upper()
    score = float(readiness_score)

    recommendation: str
    conditions: list[str] = []
    blockers: list[str] = []

    if risk == "HIGH":
        if score < 0.9:
            recommendation = UnlockRecommendation.HOLD
            blockers.append("readiness_score_below_0.9_for_HIGH_risk")
            conditions.append("achieve_readiness_score_above_0.9")
            conditions.append("complete_all_high_risk_reviews")
        else:
            recommendation = UnlockRecommendation.PROMOTE
            conditions.append("human_approval_required")
    elif risk == "MEDIUM":
        if score < 0.7:
            recommendation = UnlockRecommendation.HOLD
            blockers.append("readiness_score_below_0.7_for_MEDIUM_risk")
            conditions.append("achieve_readiness_score_above_0.7")
        else:
            recommendation = UnlockRecommendation.PROMOTE
            conditions.append("human_approval_required")
    elif risk == "LOW":
        if score < 0.5:
            recommendation = UnlockRecommendation.DEFER
            conditions.append("achieve_readiness_score_above_0.5")
        else:
            recommendation = UnlockRecommendation.PROMOTE
    else:
        recommendation = UnlockRecommendation.REJECT
        blockers.append(f"unknown_risk_class_{risk}")

    rid = f"rec_{file_path}_{risk}_{score:.2f}"

    return UnlockRecommendation(
        recommendation_id=rid,
        file_path=file_path,
        risk_class=risk,
        readiness_score=score,
        recommendation=recommendation,
        conditions=tuple(conditions),
        blockers=tuple(blockers),
    )
