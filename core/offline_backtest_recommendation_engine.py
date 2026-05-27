"""Offline backtest recommendation engine — pure functions, no I/O.

Generates, ranks, and filters backtest recommendations based on
scorecard, comparison, and robustness results.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BacktestRecommendation:
    """A single backtest recommendation."""
    recommendation_id: str
    action: str  # PROMOTE / COLLECT_MORE_DATA / REJECT_OVERFIT / TIGHTEN_RISK / WIDEN_SAMPLE / KEEP_HOLD
    confidence: float  # 0.0 - 1.0
    rationale: str
    param_id: str
    risk_factors: tuple[str, ...]


# ---------------------------------------------------------------------------
# action thresholds
# ---------------------------------------------------------------------------

_PROMOTE_EXPECTANCY_MIN = 0.3
_PROMOTE_WIN_RATE_MIN = 0.55
_PROMOTE_SAMPLE_QUALITY_MIN = 0.5
_PROMOTE_MAX_DD_LIMIT = -5.0

_COLLECT_EXPECTANCY_MIN = 0.0
_COLLECT_WIN_RATE_MIN = 0.45
_COLLECT_SAMPLE_QUALITY_MIN = 0.3


# ---------------------------------------------------------------------------
# core functions
# ---------------------------------------------------------------------------

def generate_backtest_recommendations(
    scorecards: list[dict],
    comparison: dict,
    robustness: dict | None = None,
) -> tuple[BacktestRecommendation, ...]:
    """Generate recommendations from scorecard entries and comparison data.

    Parameters
    ----------
    scorecards : list[dict]
        Each dict has ``cell_id``, ``symbol``, ``timeframe``, ``param_label``,
        ``grade``, ``reason_codes``, ``blockers``, and ``metrics``.
    comparison : dict
        Comparison result with ``best_by_metric``.
    robustness : dict, optional
        Robustness results (reserved for future use).

    Returns
    -------
    tuple[BacktestRecommendation, ...]
    """
    if not scorecards:
        return ()

    recommendations: list[BacktestRecommendation] = []
    best_by_metric = comparison.get("best_by_metric", {})

    for idx, sc in enumerate(scorecards):
        rec = _evaluate_scorecard_entry(sc, idx, best_by_metric, robustness)
        recommendations.append(rec)

    return tuple(recommendations)


def rank_recommendations(
    recommendations: tuple[BacktestRecommendation, ...],
) -> tuple[BacktestRecommendation, ...]:
    """Sort recommendations by action priority then confidence (descending).

    Priority order: PROMOTE > KEEP_HOLD > COLLECT_MORE_DATA > TIGHTEN_RISK > WIDEN_SAMPLE > REJECT_OVERFIT.
    """
    action_order = {
        "PROMOTE": 0,
        "KEEP_HOLD": 1,
        "COLLECT_MORE_DATA": 2,
        "TIGHTEN_RISK": 3,
        "WIDEN_SAMPLE": 4,
        "REJECT_OVERFIT": 5,
    }
    return tuple(
        sorted(
            recommendations,
            key=lambda r: (action_order.get(r.action, 99), -r.confidence),
        )
    )


# ---------------------------------------------------------------------------
# internals
# ---------------------------------------------------------------------------

def _evaluate_scorecard_entry(
    sc: dict,
    idx: int,
    best_by_metric: dict,
    robustness: dict | None,
) -> BacktestRecommendation:
    """Classify a single scorecard entry into a recommendation action."""
    cell_id = sc.get("cell_id", f"rec_{idx}")
    param_id = sc.get("param_label", "unknown")
    grade = sc.get("grade", "REJECT")
    metrics = sc.get("metrics", {})
    blockers = sc.get("blockers", [])

    expectancy = metrics.get("expectancy_r", 0.0)
    win_rate = metrics.get("win_rate", 0.0)
    sample_quality = metrics.get("sample_quality_score", 0.0)
    max_dd = metrics.get("max_drawdown_r", 0.0)

    risk_factors: list[str] = []
    rationale_parts: list[str] = []

    # Check if this param is best in any metric
    is_best_in_any = any(
        v == cell_id for v in best_by_metric.values()
    )

    # Risk factor checks
    if max_dd < _PROMOTE_MAX_DD_LIMIT:
        risk_factors.append(f"max_drawdown={max_dd:.2f} exceeds limit")
    if sample_quality < _COLLECT_SAMPLE_QUALITY_MIN:
        risk_factors.append(f"sample_quality={sample_quality:.2f} below minimum")
    if win_rate < 0.5:
        risk_factors.append(f"win_rate={win_rate:.2f} below 50%")

    # Classification logic
    if blockers:
        # Hard blockers -> reject
        action = "REJECT_OVERFIT"
        confidence = max(0.0, 1.0 - abs(expectancy) - (1.0 - sample_quality))
        confidence = min(confidence, 0.3)
        rationale_parts.append(f"Hard blockers: {', '.join(blockers)}.")
    elif (
        expectancy >= _PROMOTE_EXPECTANCY_MIN
        and win_rate >= _PROMOTE_WIN_RATE_MIN
        and sample_quality >= _PROMOTE_SAMPLE_QUALITY_MIN
        and max_dd >= _PROMOTE_MAX_DD_LIMIT
    ):
        action = "PROMOTE"
        confidence = _compute_confidence(expectancy, win_rate, sample_quality, max_dd)
        rationale_parts.append("Positive expectancy with adequate sample quality.")
        if is_best_in_any:
            rationale_parts.append("Best in at least one comparison metric.")
        if not risk_factors:
            rationale_parts.append("No significant risk factors detected.")
    elif (
        expectancy >= _COLLECT_EXPECTANCY_MIN
        and win_rate >= _COLLECT_WIN_RATE_MIN
        and sample_quality >= _COLLECT_SAMPLE_QUALITY_MIN
    ):
        # Marginal edge — recommend based on specific weakness
        if sample_quality < _PROMOTE_SAMPLE_QUALITY_MIN:
            action = "COLLECT_MORE_DATA"
            confidence = _compute_confidence(expectancy, win_rate, sample_quality, max_dd) * 0.6
            rationale_parts.append("Marginal edge; sample quality insufficient for promotion.")
        elif max_dd < _PROMOTE_MAX_DD_LIMIT:
            action = "TIGHTEN_RISK"
            confidence = _compute_confidence(expectancy, win_rate, sample_quality, max_dd) * 0.7
            rationale_parts.append("Drawdown exceeds promotion limit; tighten risk parameters.")
        else:
            action = "WIDEN_SAMPLE"
            confidence = _compute_confidence(expectancy, win_rate, sample_quality, max_dd) * 0.5
            rationale_parts.append("Needs broader sample coverage before decision.")
    elif expectancy > 0:
        action = "WIDEN_SAMPLE"
        confidence = max(0.1, abs(expectancy) * 0.5)
        rationale_parts.append("Weak positive expectancy; needs more data.")
    else:
        action = "KEEP_HOLD"
        confidence = 0.1
        rationale_parts.append("No edge detected; keep on hold.")

    return BacktestRecommendation(
        recommendation_id=f"rec_{idx:04d}",
        action=action,
        confidence=round(confidence, 4),
        rationale=" ".join(rationale_parts),
        param_id=param_id,
        risk_factors=tuple(risk_factors),
    )


def _compute_confidence(
    expectancy: float,
    win_rate: float,
    sample_quality: float,
    max_dd: float,
) -> float:
    """Compute confidence score in [0, 1]."""
    e_score = min(expectancy / 1.0, 1.0) if expectancy > 0 else 0.0
    w_score = win_rate
    q_score = sample_quality
    dd_score = max(0.0, 1.0 + max_dd / 10.0)  # -10 dd => 0, 0 dd => 1
    return (e_score * 0.35 + w_score * 0.25 + q_score * 0.25 + dd_score * 0.15)
