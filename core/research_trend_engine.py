"""Research trend engine — multi-run trend analysis.

Program D: Multi-Run Trend Engine.
For 3+ bundles, compute trends and detect patterns.

No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from core.research_comparison_metrics import ExtractedMetrics


@dataclass(frozen=True)
class MetricTrend:
    """Trend for a single metric across runs."""
    metric: str
    values: Tuple[float, ...]
    trend_type: str  # monotonic_improvement / monotonic_regression / noisy / stable
    slope: float
    changed: bool


@dataclass(frozen=True)
class TrendReport:
    """Multi-run trend report."""
    bundle_count: int
    labels: Tuple[str, ...]
    metric_trends: Tuple[MetricTrend, ...]
    detections: Tuple[str, ...]  # detected patterns
    overall_trend: str  # improving / regressing / stable / mixed


def compute_trend_report(
    metrics: Tuple[ExtractedMetrics, ...],
) -> TrendReport:
    """Compute trend report for 3+ bundles."""
    if len(metrics) < 3:
        raise ValueError(f"Need at least 3 bundles for trend, got {len(metrics)}")

    labels = tuple(m.label for m in metrics)

    # Metric lists
    metric_lists: Dict[str, Tuple[float, ...]] = {
        "composite_score": tuple(m.composite_score for m in metrics),
        "blocker_count": tuple(float(m.blocker_count) for m in metrics),
        "warning_count": tuple(float(m.warning_count) for m in metrics),
        "stability_score": tuple(m.stability_score for m in metrics),
        "parameter_fragility": tuple(m.parameter_fragility for m in metrics),
        "negative_control_margin": tuple(m.negative_control_margin for m in metrics),
        "overlap_risk": tuple(m.overlap_risk for m in metrics),
        "bootstrap_ci_width": tuple(m.bootstrap_ci_width for m in metrics),
        "bootstrap_worst_case": tuple(m.bootstrap_worst_case for m in metrics),
        "regime_concentration_warning_count": tuple(float(m.regime_concentration_warning_count) for m in metrics),
        "portfolio_crowding_score": tuple(m.portfolio_crowding_score for m in metrics),
    }

    trends: List[MetricTrend] = []
    detections: List[str] = []

    lower_is_better = {
        "parameter_fragility", "overlap_risk", "bootstrap_ci_width",
        "portfolio_crowding_score", "blocker_count", "warning_count",
        "regime_concentration_warning_count",
    }

    for name, values in sorted(metric_lists.items()):
        t = _analyze_trend(name, values, lower_is_better)
        trends.append(t)

        if t.trend_type == "monotonic_improvement":
            detections.append(f"{name}: monotonic_improvement")
        elif t.trend_type == "monotonic_regression":
            detections.append(f"{name}: monotonic_regression")
        elif t.trend_type == "noisy":
            detections.append(f"{name}: noisy")

    # Safety regression check
    safety_stable = all(
        m.release_hold == "HOLD" and m.advisory_only and m.no_network
        for m in metrics
    )
    if not safety_stable:
        detections.append("safety_regression")

    # Artifact drift detection (via reproducibility status)
    repro_statuses = set(m.reproducibility_status for m in metrics)
    if len(repro_statuses) > 1:
        detections.append("reproducibility_drift")

    # Overall trend
    improving_count = sum(1 for t in trends if t.trend_type == "monotonic_improvement")
    regressing_count = sum(1 for t in trends if t.trend_type == "monotonic_regression")

    if regressing_count > 0:
        overall = "regressing"
    elif improving_count > len(trends) // 2:
        overall = "improving"
    elif improving_count > 0 and regressing_count == 0:
        overall = "improving"
    else:
        overall = "stable"

    return TrendReport(
        bundle_count=len(metrics),
        labels=labels,
        metric_trends=tuple(trends),
        detections=tuple(sorted(detections)),
        overall_trend=overall,
    )


def trend_report_to_dict(r: TrendReport) -> Dict[str, Any]:
    """Serialize trend report to dict."""
    return {
        "schema_version": "1.0.0",
        "generated_at": "deterministic",
        "bundle_count": r.bundle_count,
        "labels": list(r.labels),
        "metric_trends": [
            {
                "metric": t.metric,
                "values": list(t.values),
                "trend_type": t.trend_type,
                "slope": round(t.slope, 6),
                "changed": t.changed,
            }
            for t in r.metric_trends
        ],
        "detections": list(r.detections),
        "overall_trend": r.overall_trend,
    }


def _analyze_trend(
    name: str,
    values: Tuple[float, ...],
    lower_is_better: set,
) -> MetricTrend:
    """Analyze trend for a single metric series."""
    n = len(values)
    if n < 2:
        return MetricTrend(
            metric=name, values=values,
            trend_type="stable", slope=0.0, changed=False,
        )

    # Simple slope (last - first)
    slope = values[-1] - values[0]
    changed = abs(slope) > 1e-6

    # Check monotonicity
    improving_steps = 0
    regressing_steps = 0
    lib = name in lower_is_better

    for i in range(1, n):
        diff = values[i] - values[i - 1]
        if abs(diff) < 1e-6:
            continue
        if lib:
            if diff < 0:
                improving_steps += 1
            else:
                regressing_steps += 1
        else:
            if diff > 0:
                improving_steps += 1
            else:
                regressing_steps += 1

    total_steps = improving_steps + regressing_steps
    if total_steps == 0:
        trend_type = "stable"
    elif improving_steps == total_steps:
        trend_type = "monotonic_improvement"
    elif regressing_steps == total_steps:
        trend_type = "monotonic_regression"
    elif improving_steps > 0 and regressing_steps > 0:
        if max(improving_steps, regressing_steps) / total_steps > 0.7:
            # Mostly one direction
            trend_type = "monotonic_improvement" if improving_steps > regressing_steps else "monotonic_regression"
        else:
            trend_type = "noisy"
    else:
        trend_type = "stable"

    return MetricTrend(
        metric=name, values=values,
        trend_type=trend_type, slope=slope, changed=changed,
    )
