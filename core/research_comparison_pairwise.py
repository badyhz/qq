"""Research comparison pairwise — compare pairs of bundles.

Program C: Pairwise Comparison Engine.
For each pair of bundles, compare metrics and classify changes.

No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from core.research_bundle_series import BundleRecord
from core.research_comparison_metrics import ExtractedMetrics


@dataclass(frozen=True)
class MetricDelta:
    """Single metric comparison delta."""
    metric: str
    left_value: Any
    right_value: Any
    delta: Any
    classification: str  # IMPROVED / REGRESSED / STABLE / MIXED


@dataclass(frozen=True)
class PairwiseComparison:
    """Pairwise comparison between two bundles."""
    left_label: str
    right_label: str
    overall_classification: str  # IMPROVED / REGRESSED / STABLE / MIXED / SAFETY_FAIL
    safety_fail: bool
    verdict_changed: bool
    verdict_left: str
    verdict_right: str
    composite_score_delta: float
    blocker_change: int
    warning_change: int
    safety_flag_changes: Tuple[str, ...]
    metric_deltas: Tuple[MetricDelta, ...]
    artifact_changes: Dict[str, Any]


def compare_pairwise(
    left: ExtractedMetrics,
    right: ExtractedMetrics,
    left_record: BundleRecord,
    right_record: BundleRecord,
) -> PairwiseComparison:
    """Compare two bundles pairwise."""
    # Safety flag check
    safety_changes: List[str] = []
    for flag in ("release_hold", "advisory_only", "human_review_required",
                 "no_live", "no_submit", "no_exchange", "no_network"):
        lv = getattr(left, flag, None)
        rv = getattr(right, flag, None)
        if lv != rv:
            safety_changes.append(f"{flag}: {lv!r} -> {rv!r}")

    safety_fail = len(safety_changes) > 0

    # Verdict
    verdict_changed = left.verdict != right.verdict

    # Score delta
    score_delta = right.composite_score - left.composite_score

    # Blocker/warning change
    blocker_change = right.blocker_count - left.blocker_count
    warning_change = right.warning_count - left.warning_count

    # Metric deltas
    deltas: List[MetricDelta] = []
    _float_metrics = [
        ("composite_score", left.composite_score, right.composite_score),
        ("evidence_completeness", left.evidence_completeness, right.evidence_completeness),
        ("stability_score", left.stability_score, right.stability_score),
        ("parameter_fragility", left.parameter_fragility, right.parameter_fragility),
        ("overlap_risk", left.overlap_risk, right.overlap_risk),
        ("negative_control_margin", left.negative_control_margin, right.negative_control_margin),
        ("bootstrap_ci_width", left.bootstrap_ci_width, right.bootstrap_ci_width),
        ("bootstrap_worst_case", left.bootstrap_worst_case, right.bootstrap_worst_case),
        ("portfolio_crowding_score", left.portfolio_crowding_score, right.portfolio_crowding_score),
    ]

    for name, lv, rv in _float_metrics:
        delta = rv - lv
        cls = _classify_delta(name, delta)
        deltas.append(MetricDelta(
            metric=name, left_value=lv, right_value=rv,
            delta=round(delta, 6), classification=cls,
        ))

    # Integer metrics
    _int_metrics = [
        ("blocker_count", left.blocker_count, right.blocker_count),
        ("warning_count", left.warning_count, right.warning_count),
        ("regime_concentration_warning_count", left.regime_concentration_warning_count, right.regime_concentration_warning_count),
    ]

    for name, lv, rv in _int_metrics:
        delta = rv - lv
        cls = _classify_delta(name, delta)
        deltas.append(MetricDelta(
            metric=name, left_value=lv, right_value=rv,
            delta=delta, classification=cls,
        ))

    # Artifact changes
    left_hashes = left_record.artifact_hashes
    right_hashes = right_record.artifact_hashes
    all_names = sorted(set(list(left_hashes.keys()) + list(right_hashes.keys())))

    added = [n for n in all_names if n not in left_hashes and n in right_hashes]
    removed = [n for n in all_names if n in left_hashes and n not in right_hashes]
    changed = [n for n in all_names if n in left_hashes and n in right_hashes and left_hashes[n] != right_hashes[n]]
    unchanged = [n for n in all_names if n in left_hashes and n in right_hashes and left_hashes[n] == right_hashes[n]]

    artifact_changes = {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
    }

    # Overall classification
    if safety_fail:
        overall = "SAFETY_FAIL"
    elif any(d.classification == "REGRESSED" for d in deltas):
        overall = "REGRESSED"
    elif any(d.classification == "IMPROVED" for d in deltas):
        if any(d.classification == "REGRESSED" for d in deltas):
            overall = "MIXED"
        else:
            overall = "IMPROVED"
    elif all(d.classification == "STABLE" for d in deltas):
        overall = "STABLE"
    else:
        overall = "MIXED"

    return PairwiseComparison(
        left_label=left.label,
        right_label=right.label,
        overall_classification=overall,
        safety_fail=safety_fail,
        verdict_changed=verdict_changed,
        verdict_left=left.verdict,
        verdict_right=right.verdict,
        composite_score_delta=round(score_delta, 6),
        blocker_change=blocker_change,
        warning_change=warning_change,
        safety_flag_changes=tuple(safety_changes),
        metric_deltas=tuple(deltas),
        artifact_changes=artifact_changes,
    )


def compare_all_pairs(
    metrics: Tuple[ExtractedMetrics, ...],
    records: Tuple[BundleRecord, ...],
) -> Tuple[PairwiseComparison, ...]:
    """Compare all pairs of bundles."""
    comparisons: List[PairwiseComparison] = []
    for i in range(len(metrics)):
        for j in range(i + 1, len(metrics)):
            comp = compare_pairwise(metrics[i], metrics[j], records[i], records[j])
            comparisons.append(comp)
    return tuple(comparisons)


def pairwise_to_dict(c: PairwiseComparison) -> Dict[str, Any]:
    """Serialize pairwise comparison to dict."""
    return {
        "left_label": c.left_label,
        "right_label": c.right_label,
        "overall_classification": c.overall_classification,
        "safety_fail": c.safety_fail,
        "verdict_changed": c.verdict_changed,
        "verdict_left": c.verdict_left,
        "verdict_right": c.verdict_right,
        "composite_score_delta": c.composite_score_delta,
        "blocker_change": c.blocker_change,
        "warning_change": c.warning_change,
        "safety_flag_changes": list(c.safety_flag_changes),
        "metric_deltas": [
            {
                "metric": d.metric,
                "left_value": d.left_value,
                "right_value": d.right_value,
                "delta": d.delta,
                "classification": d.classification,
            }
            for d in c.metric_deltas
        ],
        "artifact_changes": c.artifact_changes,
    }


def build_pairwise_comparison_json(
    comparisons: Tuple[PairwiseComparison, ...],
    generated_at: str = "deterministic",
) -> Dict[str, Any]:
    """Build pairwise_comparison.json content."""
    return {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "comparison_count": len(comparisons),
        "comparisons": [pairwise_to_dict(c) for c in comparisons],
    }


def _classify_delta(metric: str, delta: float) -> str:
    """Classify a metric delta as IMPROVED/REGRESSED/STABLE."""
    # Metrics where lower is better
    lower_is_better = {
        "parameter_fragility", "overlap_risk", "bootstrap_ci_width",
        "portfolio_crowding_score", "blocker_count", "warning_count",
        "regime_concentration_warning_count",
    }
    # Metrics where higher is better
    higher_is_better = {
        "composite_score", "evidence_completeness", "stability_score",
        "negative_control_margin", "bootstrap_worst_case",
    }

    threshold = 1e-6

    if abs(delta) < threshold:
        return "STABLE"

    if metric in lower_is_better:
        return "IMPROVED" if delta < 0 else "REGRESSED"
    elif metric in higher_is_better:
        return "IMPROVED" if delta > 0 else "REGRESSED"
    else:
        # Unknown metric direction
        return "STABLE" if abs(delta) < 0.01 else "MIXED"
