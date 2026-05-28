"""Research comparison regression — detect material regressions.

Program E: Regression Detector.
Detect regressions across bundle comparisons.

No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from core.research_comparison_metrics import ExtractedMetrics


@dataclass(frozen=True)
class Regression:
    """Single regression finding."""
    category: str
    description: str
    severity: str  # HIGH / MEDIUM / LOW
    metric: str
    left_value: Any
    right_value: Any


@dataclass(frozen=True)
class RegressionReport:
    """Regression detection report."""
    has_regressions: bool
    regression_count: int
    regressions: Tuple[Regression, ...]
    safety_regressions: Tuple[Regression, ...]
    metric_regressions: Tuple[Regression, ...]
    status: str  # PASS / FAIL


def detect_regressions(
    left: ExtractedMetrics,
    right: ExtractedMetrics,
    score_drop_threshold: float = 0.10,
    fragility_threshold: float = 0.40,
    overlap_threshold: float = 0.70,
    nc_margin_threshold: float = 0.10,
    bootstrap_width_threshold: float = 0.40,
) -> RegressionReport:
    """Detect material regressions between two bundles."""
    regressions: List[Regression] = []
    safety_regressions: List[Regression] = []
    metric_regressions: List[Regression] = []

    # --- Safety flag regressions ---
    if left.release_hold != right.release_hold:
        r = Regression(
            category="safety", severity="HIGH",
            description=f"release_hold changed: {left.release_hold} -> {right.release_hold}",
            metric="release_hold",
            left_value=left.release_hold, right_value=right.release_hold,
        )
        regressions.append(r)
        safety_regressions.append(r)

    if left.advisory_only != right.advisory_only:
        r = Regression(
            category="safety", severity="HIGH",
            description=f"advisory_only changed: {left.advisory_only} -> {right.advisory_only}",
            metric="advisory_only",
            left_value=left.advisory_only, right_value=right.advisory_only,
        )
        regressions.append(r)
        safety_regressions.append(r)

    if left.human_review_required != right.human_review_required:
        r = Regression(
            category="safety", severity="HIGH",
            description=f"human_review_required changed: {left.human_review_required} -> {right.human_review_required}",
            metric="human_review_required",
            left_value=left.human_review_required, right_value=right.human_review_required,
        )
        regressions.append(r)
        safety_regressions.append(r)

    if left.no_network != right.no_network:
        r = Regression(
            category="safety", severity="HIGH",
            description=f"no_network changed: {left.no_network} -> {right.no_network}",
            metric="no_network",
            left_value=left.no_network, right_value=right.no_network,
        )
        regressions.append(r)
        safety_regressions.append(r)

    # --- Score drop ---
    score_drop = left.composite_score - right.composite_score
    if score_drop > score_drop_threshold:
        r = Regression(
            category="metric", severity="HIGH" if score_drop > 0.20 else "MEDIUM",
            description=f"Composite score dropped {score_drop:.4f} (threshold {score_drop_threshold})",
            metric="composite_score",
            left_value=left.composite_score, right_value=right.composite_score,
        )
        regressions.append(r)
        metric_regressions.append(r)

    # --- Blocker increase ---
    if right.blocker_count > left.blocker_count:
        r = Regression(
            category="metric", severity="HIGH",
            description=f"Blocker count increased: {left.blocker_count} -> {right.blocker_count}",
            metric="blocker_count",
            left_value=left.blocker_count, right_value=right.blocker_count,
        )
        regressions.append(r)
        metric_regressions.append(r)

    # --- Negative control margin drop ---
    if left.negative_control_margin >= nc_margin_threshold and right.negative_control_margin < nc_margin_threshold:
        r = Regression(
            category="metric", severity="HIGH",
            description=f"Negative control margin dropped below {nc_margin_threshold}: {right.negative_control_margin:.4f}",
            metric="negative_control_margin",
            left_value=left.negative_control_margin, right_value=right.negative_control_margin,
        )
        regressions.append(r)
        metric_regressions.append(r)

    # --- Parameter fragility rise ---
    if right.parameter_fragility > fragility_threshold and left.parameter_fragility <= fragility_threshold:
        r = Regression(
            category="metric", severity="MEDIUM",
            description=f"Parameter fragility rose above {fragility_threshold}: {right.parameter_fragility:.4f}",
            metric="parameter_fragility",
            left_value=left.parameter_fragility, right_value=right.parameter_fragility,
        )
        regressions.append(r)
        metric_regressions.append(r)

    # --- Overlap risk rise ---
    if right.overlap_risk > overlap_threshold and left.overlap_risk <= overlap_threshold:
        r = Regression(
            category="metric", severity="MEDIUM",
            description=f"Overlap risk rose above {overlap_threshold}: {right.overlap_risk:.4f}",
            metric="overlap_risk",
            left_value=left.overlap_risk, right_value=right.overlap_risk,
        )
        regressions.append(r)
        metric_regressions.append(r)

    # --- Bootstrap uncertainty widen ---
    if right.bootstrap_ci_width > bootstrap_width_threshold and left.bootstrap_ci_width <= bootstrap_width_threshold:
        r = Regression(
            category="metric", severity="MEDIUM",
            description=f"Bootstrap CI width widened above {bootstrap_width_threshold}: {right.bootstrap_ci_width:.4f}",
            metric="bootstrap_ci_width",
            left_value=left.bootstrap_ci_width, right_value=right.bootstrap_ci_width,
        )
        regressions.append(r)
        metric_regressions.append(r)

    # --- Regime concentration worsen ---
    if right.regime_concentration_warning_count > left.regime_concentration_warning_count:
        r = Regression(
            category="metric", severity="MEDIUM",
            description=f"Regime concentration warnings increased: {left.regime_concentration_warning_count} -> {right.regime_concentration_warning_count}",
            metric="regime_concentration_warning_count",
            left_value=left.regime_concentration_warning_count, right_value=right.regime_concentration_warning_count,
        )
        regressions.append(r)
        metric_regressions.append(r)

    # --- Reproducibility broken ---
    if left.reproducibility_status == "PASS" and right.reproducibility_status != "PASS":
        r = Regression(
            category="metric", severity="HIGH",
            description=f"Reproducibility broken: {left.reproducibility_status} -> {right.reproducibility_status}",
            metric="reproducibility_status",
            left_value=left.reproducibility_status, right_value=right.reproducibility_status,
        )
        regressions.append(r)
        metric_regressions.append(r)

    status = "FAIL" if safety_regressions else ("FAIL" if len(regressions) > 0 else "PASS")

    return RegressionReport(
        has_regressions=len(regressions) > 0,
        regression_count=len(regressions),
        regressions=tuple(regressions),
        safety_regressions=tuple(safety_regressions),
        metric_regressions=tuple(metric_regressions),
        status=status,
    )


def regression_report_to_dict(r: RegressionReport) -> Dict[str, Any]:
    """Serialize regression report to dict."""
    return {
        "schema_version": "1.0.0",
        "generated_at": "deterministic",
        "has_regressions": r.has_regressions,
        "regression_count": r.regression_count,
        "regressions": [
            {
                "category": reg.category,
                "description": reg.description,
                "severity": reg.severity,
                "metric": reg.metric,
                "left_value": reg.left_value,
                "right_value": reg.right_value,
            }
            for reg in r.regressions
        ],
        "safety_regressions_count": len(r.safety_regressions),
        "metric_regressions_count": len(r.metric_regressions),
        "status": r.status,
    }
