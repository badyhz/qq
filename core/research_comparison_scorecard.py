"""Research comparison scorecard — human-readable scorecard.

Program F: Comparison Scorecard.
Build a single scorecard summarizing the best bundle in each category.

No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from core.research_comparison_metrics import ExtractedMetrics


@dataclass(frozen=True)
class ComparisonScorecard:
    """Comparison scorecard across bundles."""
    best_composite_score: str
    best_composite_score_value: float
    safest_bundle: str
    safest_reason: str
    most_robust_bundle: str
    most_robust_value: float
    least_fragile: str
    least_fragile_value: float
    best_negative_control: str
    best_negative_control_value: float
    lowest_overlap: str
    lowest_overlap_value: float
    lowest_regime_concentration: str
    lowest_regime_concentration_value: int
    most_reproducible: str
    review_priority: Tuple[str, ...]
    advisory_only: bool
    promotion_blocked: bool
    promotion_block_reason: str


def build_scorecard(
    metrics: Tuple[ExtractedMetrics, ...],
) -> ComparisonScorecard:
    """Build comparison scorecard from extracted metrics."""
    if not metrics:
        raise ValueError("No metrics provided")

    # Best composite score
    best_score = max(metrics, key=lambda m: m.composite_score)

    # Safest bundle (most safety flags true, lowest risk)
    def _safety_score(m: ExtractedMetrics) -> float:
        score = 0.0
        if m.release_hold == "HOLD":
            score += 10
        if m.advisory_only:
            score += 5
        if m.human_review_required:
            score += 5
        if m.no_network:
            score += 3
        if m.no_live:
            score += 3
        if m.no_submit:
            score += 3
        if m.no_exchange:
            score += 3
        # Prefer fewer blockers and warnings
        score -= m.blocker_count * 2
        score -= m.warning_count
        return score

    safest = max(metrics, key=_safety_score)
    safest_reason_parts = []
    if safest.release_hold == "HOLD":
        safest_reason_parts.append("release_hold=HOLD")
    if safest.advisory_only:
        safest_reason_parts.append("advisory_only")
    if safest.no_network:
        safest_reason_parts.append("no_network")
    safest_reason = ", ".join(safest_reason_parts) if safest_reason_parts else "all flags valid"

    # Most robust (highest stability)
    most_robust = max(metrics, key=lambda m: m.stability_score)

    # Least fragile
    least_fragile = min(metrics, key=lambda m: m.parameter_fragility)

    # Best negative control margin
    best_nc = max(metrics, key=lambda m: m.negative_control_margin)

    # Lowest overlap risk
    lowest_overlap = min(metrics, key=lambda m: m.overlap_risk)

    # Lowest regime concentration warnings
    lowest_regime = min(metrics, key=lambda m: m.regime_concentration_warning_count)

    # Most reproducible
    most_reproducible = max(
        metrics,
        key=lambda m: 1 if m.reproducibility_status == "PASS" else 0,
    )

    # Review priority: order by composite score descending
    review_priority = tuple(
        m.label for m in sorted(metrics, key=lambda m: m.composite_score, reverse=True)
    )

    # Advisory / promotion
    advisory_only = all(m.advisory_only for m in metrics)
    promotion_blocked = True  # Always blocked until human review
    promotion_block_reason = "Human review required. Advisory only. No auto-promotion."

    return ComparisonScorecard(
        best_composite_score=best_score.label,
        best_composite_score_value=best_score.composite_score,
        safest_bundle=safest.label,
        safest_reason=safest_reason,
        most_robust_bundle=most_robust.label,
        most_robust_value=most_robust.stability_score,
        least_fragile=least_fragile.label,
        least_fragile_value=least_fragile.parameter_fragility,
        best_negative_control=best_nc.label,
        best_negative_control_value=best_nc.negative_control_margin,
        lowest_overlap=lowest_overlap.label,
        lowest_overlap_value=lowest_overlap.overlap_risk,
        lowest_regime_concentration=lowest_regime.label,
        lowest_regime_concentration_value=lowest_regime.regime_concentration_warning_count,
        most_reproducible=most_reproducible.label,
        review_priority=review_priority,
        advisory_only=advisory_only,
        promotion_blocked=promotion_blocked,
        promotion_block_reason=promotion_block_reason,
    )


def scorecard_to_dict(s: ComparisonScorecard) -> Dict[str, Any]:
    """Serialize scorecard to dict."""
    return {
        "schema_version": "1.0.0",
        "generated_at": "deterministic",
        "best_composite_score": s.best_composite_score,
        "best_composite_score_value": s.best_composite_score_value,
        "safest_bundle": s.safest_bundle,
        "safest_reason": s.safest_reason,
        "most_robust_bundle": s.most_robust_bundle,
        "most_robust_value": s.most_robust_value,
        "least_fragile": s.least_fragile,
        "least_fragile_value": s.least_fragile_value,
        "best_negative_control": s.best_negative_control,
        "best_negative_control_value": s.best_negative_control_value,
        "lowest_overlap": s.lowest_overlap,
        "lowest_overlap_value": s.lowest_overlap_value,
        "lowest_regime_concentration": s.lowest_regime_concentration,
        "lowest_regime_concentration_value": s.lowest_regime_concentration_value,
        "most_reproducible": s.most_reproducible,
        "review_priority": list(s.review_priority),
        "advisory_only": s.advisory_only,
        "promotion_blocked": s.promotion_blocked,
        "promotion_block_reason": s.promotion_block_reason,
    }
