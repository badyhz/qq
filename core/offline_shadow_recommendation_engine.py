"""Offline shadow recommendation engine -- pure functions, no I/O.

Generates, ranks, and filters experiment recommendations based on
metric results from the offline shadow research pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Recommendation:
    experiment_id: str
    action: str  # DEPLOY / WATCH / REJECT
    confidence: float  # 0.0 - 1.0
    rationale: str
    risk_factors: tuple[str, ...]
    next_steps: tuple[str, ...]


# ---------------------------------------------------------------------------
# action thresholds
# ---------------------------------------------------------------------------

_DEPLOY_EXPECTANCY_MIN = 0.3
_DEPLOY_WIN_RATE_MIN = 0.55
_DEPLOY_SAMPLE_QUALITY_MIN = 0.5
_DEPLOY_MAX_DD_LIMIT = -5.0

_WATCH_EXPECTANCY_MIN = 0.0
_WATCH_WIN_RATE_MIN = 0.45
_WATCH_SAMPLE_QUALITY_MIN = 0.3


# ---------------------------------------------------------------------------
# core functions
# ---------------------------------------------------------------------------

def generate_recommendations(experiment_results: list[dict]) -> list[Recommendation]:
    """Generate recommendations from experiment result dicts.

    Parameters
    ----------
    experiment_results : list[dict]
        Each dict must have ``experiment_id`` and metric fields produced by
        :func:`compute_run_metrics` or :func:`compute_aggregate_metrics`.
        Required keys: ``experiment_id``, ``expectancy_r``, ``win_rate``,
        ``sample_quality_score``, ``max_drawdown_r``.

    Returns
    -------
    list[Recommendation]
    """
    if not experiment_results:
        return []

    recommendations: list[Recommendation] = []
    for result in experiment_results:
        rec = _evaluate_single(result)
        recommendations.append(rec)
    return recommendations


def rank_recommendations(recommendations: list[Recommendation]) -> list[Recommendation]:
    """Sort recommendations by action priority then confidence (descending).

    Priority order: DEPLOY > WATCH > REJECT.
    """
    action_order = {"DEPLOY": 0, "WATCH": 1, "REJECT": 2}
    return sorted(
        recommendations,
        key=lambda r: (action_order.get(r.action, 99), -r.confidence),
    )


def filter_recommendations(
    recommendations: list[Recommendation],
    criteria: dict[str, Any] | None = None,
) -> list[Recommendation]:
    """Filter recommendations by criteria dict.

    Supported criteria keys:
    - ``action``: str or list[str] -- keep only matching actions
    - ``min_confidence``: float -- keep only recs with confidence >= value
    - ``max_risk_factors``: int -- keep only recs with <= N risk factors
    """
    if not criteria:
        return list(recommendations)

    result: list[Recommendation] = []
    for rec in recommendations:
        if not _matches_criteria(rec, criteria):
            continue
        result.append(rec)
    return result


# ---------------------------------------------------------------------------
# internals
# ---------------------------------------------------------------------------

def _evaluate_single(result: dict) -> Recommendation:
    """Classify a single experiment result into DEPLOY / WATCH / REJECT."""
    eid = result.get("experiment_id", "unknown")
    expectancy = result.get("expectancy_r", 0.0)
    win_rate = result.get("win_rate", 0.0)
    sample_quality = result.get("sample_quality_score", 0.0)
    max_dd = result.get("max_drawdown_r", 0.0)

    risk_factors: list[str] = []
    rationale_parts: list[str] = []

    # check risk factors
    if max_dd < _DEPLOY_MAX_DD_LIMIT:
        risk_factors.append(f"max_drawdown={max_dd:.2f} exceeds limit")
    if sample_quality < _WATCH_SAMPLE_QUALITY_MIN:
        risk_factors.append(f"sample_quality={sample_quality:.2f} below minimum")
    if win_rate < 0.5:
        risk_factors.append(f"win_rate={win_rate:.2f} below 50%")

    # classify
    if (
        expectancy >= _DEPLOY_EXPECTANCY_MIN
        and win_rate >= _DEPLOY_WIN_RATE_MIN
        and sample_quality >= _DEPLOY_SAMPLE_QUALITY_MIN
        and max_dd >= _DEPLOY_MAX_DD_LIMIT
    ):
        action = "DEPLOY"
        confidence = _compute_confidence(expectancy, win_rate, sample_quality, max_dd)
        rationale_parts.append("Positive expectancy with adequate sample quality.")
        if not risk_factors:
            rationale_parts.append("No significant risk factors detected.")
        next_steps = (
            "Proceed to paper trading validation.",
            "Set up real-time monitoring.",
        )
    elif (
        expectancy >= _WATCH_EXPECTANCY_MIN
        and win_rate >= _WATCH_WIN_RATE_MIN
        and sample_quality >= _WATCH_SAMPLE_QUALITY_MIN
    ):
        action = "WATCH"
        confidence = _compute_confidence(expectancy, win_rate, sample_quality, max_dd) * 0.7
        rationale_parts.append("Marginal edge detected; needs more data or tuning.")
        next_steps = (
            "Collect more samples.",
            "Test across additional timeframes.",
        )
    else:
        action = "REJECT"
        confidence = max(
            0.0,
            1.0 - abs(expectancy) - (1.0 - sample_quality),
        )
        confidence = min(confidence, 0.3)
        rationale_parts.append("Insufficient edge or sample quality.")
        next_steps = (
            "Revise parameter set.",
            "Investigate data quality.",
        )

    return Recommendation(
        experiment_id=eid,
        action=action,
        confidence=round(confidence, 4),
        rationale=" ".join(rationale_parts),
        risk_factors=tuple(risk_factors),
        next_steps=next_steps,
    )


def _compute_confidence(
    expectancy: float,
    win_rate: float,
    sample_quality: float,
    max_dd: float,
) -> float:
    """Compute confidence score in [0, 1]."""
    # Normalize each component to [0, 1]
    e_score = min(expectancy / 1.0, 1.0) if expectancy > 0 else 0.0
    w_score = win_rate  # already 0-1
    q_score = sample_quality  # already 0-1
    dd_score = max(0.0, 1.0 + max_dd / 10.0)  # -10 dd => 0, 0 dd => 1

    return (e_score * 0.35 + w_score * 0.25 + q_score * 0.25 + dd_score * 0.15)


def _matches_criteria(rec: Recommendation, criteria: dict) -> bool:
    """Check if a recommendation matches all specified criteria."""
    if "action" in criteria:
        allowed = criteria["action"]
        if isinstance(allowed, str):
            allowed = [allowed]
        if rec.action not in allowed:
            return False

    if "min_confidence" in criteria:
        if rec.confidence < criteria["min_confidence"]:
            return False

    if "max_risk_factors" in criteria:
        if len(rec.risk_factors) > criteria["max_risk_factors"]:
            return False

    return True
