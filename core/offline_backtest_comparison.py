"""Offline backtest parameter comparison engine — pure functions.

Compares scorecards to detect stable winners, overfit candidates,
drawdown regression, sample weakness, and symbol inconsistency.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, Sequence


@dataclass(frozen=True)
class ComparisonResult:
    """Immutable result of parameter set comparison."""
    comparison_id: str
    best_param_id: str
    worst_param_id: str
    stable_winner: bool
    overfit_candidate: bool
    drawdown_regression: bool
    sample_weakness: bool
    symbol_inconsistency: bool
    recommendations: tuple  # tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.comparison_id:
            raise ValueError("comparison_id must be non-empty")
        if not isinstance(self.recommendations, tuple):
            raise ValueError("recommendations must be a tuple")


def _extract_param_id(scorecard: Dict[str, Any]) -> str:
    """Extract param_id from a scorecard or run result."""
    return str(
        scorecard.get("param_id")
        or scorecard.get("run_id")
        or scorecard.get("scorecard_id")
        or "unknown"
    )


def _quality_score(sc: Dict[str, Any]) -> float:
    """Extract quality_adjusted_score from a scorecard/metrics dict."""
    metrics = sc.get("metrics", sc)
    return float(metrics.get("quality_adjusted_score", 0.0))


def _max_drawdown(sc: Dict[str, Any]) -> float:
    metrics = sc.get("metrics", sc)
    return float(metrics.get("max_drawdown_r", 0.0))


def _trade_count(sc: Dict[str, Any]) -> int:
    metrics = sc.get("metrics", sc)
    return int(metrics.get("trade_count", 0))


def _sample_adequacy(sc: Dict[str, Any]) -> float:
    metrics = sc.get("metrics", sc)
    return float(metrics.get("sample_adequacy_score", 0.0))


def _profit_factor(sc: Dict[str, Any]) -> float:
    metrics = sc.get("metrics", sc)
    return float(metrics.get("profit_factor", 0.0))


def _expectancy(sc: Dict[str, Any]) -> float:
    metrics = sc.get("metrics", sc)
    return float(metrics.get("expectancy_r", 0.0))


def _grade(sc: Dict[str, Any]) -> str:
    return str(sc.get("grade", ""))


def compare_parameter_sets(
    scorecards: Sequence[Dict[str, Any]],
    *,
    comparison_id: str = "",
) -> ComparisonResult:
    """Compare parameter sets and detect patterns.

    Each scorecard dict should have at minimum:
        param_id (or run_id), grade, metrics (or top-level metric keys)

    Returns ComparisonResult with detection flags and recommendations.
    """
    cid = comparison_id or f"CMP-{uuid.uuid4().hex[:8]}"

    if not scorecards:
        return ComparisonResult(
            comparison_id=cid,
            best_param_id="none",
            worst_param_id="none",
            stable_winner=False,
            overfit_candidate=False,
            drawdown_regression=False,
            sample_weakness=True,
            symbol_inconsistency=False,
            recommendations=("no_scorecards_to_compare",),
        )

    # Rank by quality_adjusted_score
    ranked = sorted(scorecards, key=_quality_score, reverse=True)
    best = ranked[0]
    worst = ranked[-1]

    best_id = _extract_param_id(best)
    worst_id = _extract_param_id(worst)

    # Count grades
    grades = [_grade(sc) for sc in scorecards]
    pass_count = grades.count("PASS")
    reject_count = grades.count("REJECT")
    watch_count = grades.count("WATCH")
    insufficient_count = grades.count("INSUFFICIENT_SAMPLE")
    total = len(scorecards)

    # --- Detection logic ---
    recommendations: list[str] = []

    # stable_winner: at least one PASS with high score and good drawdown
    stable_winner = False
    if pass_count > 0:
        best_sc = best
        if (
            _quality_score(best_sc) > 0
            and _max_drawdown(best_sc) > -5.0
            and _profit_factor(best_sc) > 1.2
        ):
            stable_winner = True
            recommendations.append(
                f"param {best_id} is stable winner with "
                f"quality_score={_quality_score(best_sc):.3f}"
            )

    # overfit_candidate: best has much higher score than median, few trades
    overfit_candidate = False
    if total >= 3:
        scores = [_quality_score(sc) for sc in scorecards]
        median_score = sorted(scores)[len(scores) // 2]
        best_score = scores[0] if scores == sorted(scores, reverse=True) else max(scores)
        best_score = _quality_score(best)
        if best_score > 0 and median_score > 0:
            ratio = best_score / median_score
        else:
            ratio = 0.0
        if ratio > 3.0 and _trade_count(best) < 20:
            overfit_candidate = True
            recommendations.append(
                f"param {best_id} may be overfit: score ratio {ratio:.1f}x "
                f"median with only {_trade_count(best)} trades"
            )

    # drawdown_regression: best param has significant drawdown
    drawdown_regression = False
    if _max_drawdown(best) < -3.0:
        drawdown_regression = True
        recommendations.append(
            f"param {best_id} has drawdown_regression: "
            f"max_dd_r={_max_drawdown(best):.2f}"
        )

    # sample_weakness: majority have insufficient sample
    sample_weakness = False
    weak_count = sum(
        1 for sc in scorecards if _sample_adequacy(sc) < 0.5
    )
    if weak_count > total / 2:
        sample_weakness = True
        recommendations.append(
            f"sample_weakness: {weak_count}/{total} runs have "
            f"sample_adequacy < 0.5"
        )

    # symbol_inconsistency: high variance in expectancy across runs
    symbol_inconsistency = False
    if total >= 3:
        expectancies = [_expectancy(sc) for sc in scorecards]
        exp_mean = sum(expectancies) / len(expectancies)
        exp_var = sum((e - exp_mean) ** 2 for e in expectancies) / len(expectancies)
        exp_std = exp_var ** 0.5
        if exp_mean != 0 and abs(exp_std / exp_mean) > 1.0:
            symbol_inconsistency = True
            recommendations.append(
                f"symbol_inconsistency: expectancy CV={abs(exp_std / exp_mean):.2f}"
            )

    if not recommendations:
        recommendations.append("no_issues_detected")

    return ComparisonResult(
        comparison_id=cid,
        best_param_id=best_id,
        worst_param_id=worst_id,
        stable_winner=stable_winner,
        overfit_candidate=overfit_candidate,
        drawdown_regression=drawdown_regression,
        sample_weakness=sample_weakness,
        symbol_inconsistency=symbol_inconsistency,
        recommendations=tuple(recommendations),
    )
