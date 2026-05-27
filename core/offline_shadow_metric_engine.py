"""Offline shadow metric engine -- pure functions, no I/O, no pandas.

Computes run-level and aggregate metrics from shadow outcome records.
Each outcome dict is expected to have at minimum:
    return_r: float   (R-multiple return for the candidate)
and optionally:
    mfe_r: float      (maximum favorable excursion in R)
    mae_r: float      (maximum adverse excursion in R)
    symbol: str
    timestamp: str
"""
from __future__ import annotations

import math
from typing import Any


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


# ---------------------------------------------------------------------------
# core metric computation
# ---------------------------------------------------------------------------

def compute_run_metrics(outcomes: list[dict]) -> dict:
    """Compute all metrics for a single run from its outcome records.

    Parameters
    ----------
    outcomes : list[dict]
        Each dict must contain ``return_r`` (float).  Optional keys:
        ``mfe_r``, ``mae_r``, ``symbol``, ``timestamp``.

    Returns
    -------
    dict
        Metric dict with all required fields.
    """
    candidate_count = len(outcomes)

    if candidate_count == 0:
        return _empty_metrics()

    returns = [_safe_float(o.get("return_r", 0.0)) for o in outcomes]
    mfe_values = [_safe_float(o.get("mfe_r", 0.0)) for o in outcomes]
    mae_values = [_safe_float(o.get("mae_r", 0.0)) for o in outcomes]

    win_count = sum(1 for r in returns if r > 0)
    loss_count = sum(1 for r in returns if r < 0)
    neutral_count = candidate_count - win_count - loss_count

    win_rate = win_count / candidate_count
    loss_rate = loss_count / candidate_count

    avg_return_r = _mean(returns)

    # expectancy = win_rate * avg_win - loss_rate * avg_loss
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r < 0]
    avg_win = _mean(wins)
    avg_loss = _mean(losses)
    expectancy_r = win_rate * avg_win - loss_rate * abs(avg_loss)

    # max drawdown (worst cumulative drawdown in R)
    max_drawdown_r = _compute_max_drawdown(returns)

    avg_mfe_r = _mean(mfe_values)
    avg_mae_r = _mean(mae_values)

    # profit factor = gross_profit / abs(gross_loss)
    gross_profit = sum(wins)
    gross_loss = sum(abs(l) for l in losses)
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    # sample quality composite (0-1)
    sample_quality_score = _compute_sample_quality(
        candidate_count, mfe_values, mae_values, win_rate
    )

    # coverage status
    has_mfe = any(v != 0.0 for v in mfe_values)
    has_mae = any(v != 0.0 for v in mae_values)
    if candidate_count == 0:
        coverage_status = "empty"
    elif has_mfe and has_mae:
        coverage_status = "full"
    else:
        coverage_status = "partial"

    return {
        "candidate_count": candidate_count,
        "win_count": win_count,
        "loss_count": loss_count,
        "neutral_count": neutral_count,
        "win_rate": round(win_rate, 6),
        "avg_return_r": round(avg_return_r, 6),
        "expectancy_r": round(expectancy_r, 6),
        "max_drawdown_r": round(max_drawdown_r, 6),
        "avg_mfe_r": round(avg_mfe_r, 6),
        "avg_mae_r": round(avg_mae_r, 6),
        "profit_factor": round(profit_factor, 6),
        "sample_quality_score": round(sample_quality_score, 6),
        "coverage_status": coverage_status,
    }


def _empty_metrics() -> dict:
    return {
        "candidate_count": 0,
        "win_count": 0,
        "loss_count": 0,
        "neutral_count": 0,
        "win_rate": 0.0,
        "avg_return_r": 0.0,
        "expectancy_r": 0.0,
        "max_drawdown_r": 0.0,
        "avg_mfe_r": 0.0,
        "avg_mae_r": 0.0,
        "profit_factor": 0.0,
        "sample_quality_score": 0.0,
        "coverage_status": "empty",
    }


def _compute_max_drawdown(returns: list[float]) -> float:
    """Worst peak-to-trough drawdown on cumulative R returns.

    Returns a negative number (or 0.0 if no drawdown).
    """
    if not returns:
        return 0.0
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in returns:
        cumulative += r
        if cumulative > peak:
            peak = cumulative
        dd = cumulative - peak  # <= 0
        if dd < max_dd:
            max_dd = dd
    return max_dd


def _compute_sample_quality(
    candidate_count: int,
    mfe_values: list[float],
    mae_values: list[float],
    win_rate: float,
) -> float:
    """Composite sample quality score in [0, 1].

    Three components equally weighted:
      1. count_score   -- min(candidate_count / 10, 1.0)
      2. data_completeness -- fraction of outcomes with non-zero mfe AND mae
      3. balance_score -- 1 - |win_rate - 0.5| * 2
    """
    count_score = min(candidate_count / 10.0, 1.0)

    n = len(mfe_values)
    if n == 0:
        data_completeness = 0.0
    else:
        complete = sum(
            1 for mfe, mae in zip(mfe_values, mae_values) if mfe != 0.0 and mae != 0.0
        )
        data_completeness = complete / n

    balance_score = max(0.0, 1.0 - abs(win_rate - 0.5) * 2.0)

    return (count_score + data_completeness + balance_score) / 3.0


# ---------------------------------------------------------------------------
# aggregate across runs
# ---------------------------------------------------------------------------

def compute_aggregate_metrics(run_metrics_list: list[dict]) -> dict:
    """Aggregate metrics across multiple runs.

    Parameters
    ----------
    run_metrics_list : list[dict]
        List of dicts produced by :func:`compute_run_metrics`.

    Returns
    -------
    dict
        Aggregated metric dict (same keys as run-level plus ``run_count``).
    """
    if not run_metrics_list:
        result = _empty_metrics()
        result["run_count"] = 0
        return result

    total_candidates = sum(m.get("candidate_count", 0) for m in run_metrics_list)
    total_wins = sum(m.get("win_count", 0) for m in run_metrics_list)
    total_losses = sum(m.get("loss_count", 0) for m in run_metrics_list)
    total_neutral = sum(m.get("neutral_count", 0) for m in run_metrics_list)

    all_returns: list[float] = []
    all_mfe: list[float] = []
    all_mae: list[float] = []
    for m in run_metrics_list:
        n = m.get("candidate_count", 0)
        all_returns.extend([m.get("avg_return_r", 0.0)] * n)
        all_mfe.extend([m.get("avg_mfe_r", 0.0)] * n)
        all_mae.extend([m.get("avg_mae_r", 0.0)] * n)

    win_rate = total_wins / total_candidates if total_candidates > 0 else 0.0
    loss_rate = total_losses / total_candidates if total_candidates > 0 else 0.0
    avg_return_r = _mean(all_returns)

    # Reconstruct expectancy from aggregated parts
    avg_win = (
        sum(m.get("avg_return_r", 0.0) * m.get("win_count", 0) for m in run_metrics_list)
        / total_wins if total_wins > 0 else 0.0
    )
    avg_loss = (
        sum(abs(m.get("avg_return_r", 0.0)) * m.get("loss_count", 0) for m in run_metrics_list)
        / total_losses if total_losses > 0 else 0.0
    )
    expectancy_r = win_rate * avg_win - loss_rate * avg_loss

    max_drawdown_r = min(m.get("max_drawdown_r", 0.0) for m in run_metrics_list)

    avg_mfe_r = _mean(all_mfe)
    avg_mae_r = _mean(all_mae)

    gross_profit = sum(
        m.get("avg_return_r", 0.0) * m.get("win_count", 0)
        for m in run_metrics_list if m.get("avg_return_r", 0.0) > 0
    )
    gross_loss = sum(
        abs(m.get("avg_return_r", 0.0)) * m.get("loss_count", 0)
        for m in run_metrics_list if m.get("avg_return_r", 0.0) < 0
    )
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    sample_quality_score = _mean(
        [m.get("sample_quality_score", 0.0) for m in run_metrics_list]
    )

    has_full = any(m.get("coverage_status") == "full" for m in run_metrics_list)
    has_partial = any(m.get("coverage_status") == "partial" for m in run_metrics_list)
    if has_full and not has_partial:
        coverage_status = "full"
    elif has_full or has_partial:
        coverage_status = "partial"
    else:
        coverage_status = "empty"

    return {
        "run_count": len(run_metrics_list),
        "candidate_count": total_candidates,
        "win_count": total_wins,
        "loss_count": total_losses,
        "neutral_count": total_neutral,
        "win_rate": round(win_rate, 6),
        "avg_return_r": round(avg_return_r, 6),
        "expectancy_r": round(expectancy_r, 6),
        "max_drawdown_r": round(max_drawdown_r, 6),
        "avg_mfe_r": round(avg_mfe_r, 6),
        "avg_mae_r": round(avg_mae_r, 6),
        "profit_factor": round(profit_factor, 6),
        "sample_quality_score": round(sample_quality_score, 6),
        "coverage_status": coverage_status,
    }
