"""Offline shadow experiment comparison engine -- pure functions.

Compares two experiment results to detect improvements and regressions.
"""
from __future__ import annotations

from typing import Any


def _delta(a: float, b: float) -> float:
    """Return a - b rounded to 6 decimal places."""
    return round(a - b, 6)


def _extract_run_summary(results: dict) -> dict:
    """Pull top-level aggregate numbers from an experiment result dict.

    Works with both evaluator output and scorecard-augmented output.
    """
    runs = results.get("runs", [])

    if not runs:
        return {
            "candidate_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate": 0.0,
            "expectancy_r": 0.0,
            "max_drawdown_r": 0.0,
            "profit_factor": 0.0,
            "sample_quality_score": 0.0,
            "coverage_status": "empty",
            "run_count": 0,
        }

    total_candidates = sum(r.get("metrics", {}).get("candidate_count", 0) for r in runs)
    total_wins = sum(r.get("metrics", {}).get("win_count", 0) for r in runs)
    total_losses = sum(r.get("metrics", {}).get("loss_count", 0) for r in runs)
    win_rate = total_wins / total_candidates if total_candidates > 0 else 0.0

    # Weighted expectancy by candidate count
    weighted_exp = sum(
        r.get("metrics", {}).get("expectancy_r", 0.0)
        * r.get("metrics", {}).get("candidate_count", 0)
        for r in runs
    )
    expectancy_r = weighted_exp / total_candidates if total_candidates > 0 else 0.0

    max_drawdown_r = min(
        (r.get("metrics", {}).get("max_drawdown_r", 0.0) for r in runs), default=0.0
    )

    # Weighted profit factor
    total_gross_profit = sum(
        r.get("metrics", {}).get("profit_factor", 0.0)
        * r.get("metrics", {}).get("candidate_count", 0)
        for r in runs if r.get("metrics", {}).get("profit_factor", 0.0) != float("inf")
    )
    profit_factor = (
        total_gross_profit / total_candidates if total_candidates > 0 else 0.0
    )

    sample_quality_score = sum(
        r.get("metrics", {}).get("sample_quality_score", 0.0) for r in runs
    ) / len(runs)

    has_full = any(r.get("metrics", {}).get("coverage_status") == "full" for r in runs)
    has_partial = any(r.get("metrics", {}).get("coverage_status") == "partial" for r in runs)
    if has_full and not has_partial:
        coverage_status = "full"
    elif has_full or has_partial:
        coverage_status = "partial"
    else:
        coverage_status = "empty"

    return {
        "candidate_count": total_candidates,
        "win_count": total_wins,
        "loss_count": total_losses,
        "win_rate": round(win_rate, 6),
        "expectancy_r": round(expectancy_r, 6),
        "max_drawdown_r": round(max_drawdown_r, 6),
        "profit_factor": round(profit_factor, 6),
        "sample_quality_score": round(sample_quality_score, 6),
        "coverage_status": coverage_status,
        "run_count": len(runs),
    }


def _gate_status(results: dict) -> str:
    """Extract verdict from scorecard if present, else 'unscored'."""
    if "verdict" in results:
        return results["verdict"]
    return "unscored"


def _rank_runs(runs: list[dict]) -> list[str]:
    """Sort run_ids by expectancy_r descending."""
    scored = [
        (r.get("run_id", ""), r.get("metrics", {}).get("expectancy_r", 0.0))
        for r in runs
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [rid for rid, _ in scored]


def compare_experiments(result_a: dict, result_b: dict) -> dict:
    """Compare experiment A (baseline) vs experiment B (candidate).

    Parameters
    ----------
    result_a : dict
        Baseline experiment result (evaluator or scorecard output).
    result_b : dict
        Candidate experiment result.

    Returns
    -------
    dict
        Comparison with deltas, direction flags, and rank changes.
    """
    sum_a = _extract_run_summary(result_a)
    sum_b = _extract_run_summary(result_b)

    expectancy_delta = _delta(sum_b["expectancy_r"], sum_a["expectancy_r"])
    drawdown_delta = _delta(sum_b["max_drawdown_r"], sum_a["max_drawdown_r"])
    sample_count_delta = sum_b["candidate_count"] - sum_a["candidate_count"]
    quality_delta = _delta(sum_b["sample_quality_score"], sum_a["sample_quality_score"])

    # direction flags
    expectancy_improved = expectancy_delta > 0
    expectancy_deteriorated = expectancy_delta < 0
    drawdown_improved = drawdown_delta > 0  # less negative = better
    drawdown_deteriorated = drawdown_delta < 0

    # gate status changes
    gate_a = _gate_status(result_a)
    gate_b = _gate_status(result_b)
    gate_changed = gate_a != gate_b

    # rank changes per run
    runs_a = result_a.get("runs", [])
    runs_b = result_b.get("runs", [])
    rank_a = _rank_runs(runs_a)
    rank_b = _rank_runs(runs_b)

    # find runs present in both for rank comparison
    common_runs = set(rank_a) & set(rank_b)
    rank_changes: dict[str, dict] = []
    rank_changes_list: list[dict] = []
    for run_id in common_runs:
        pos_a = rank_a.index(run_id) if run_id in rank_a else -1
        pos_b = rank_b.index(run_id) if run_id in rank_b else -1
        if pos_a != pos_b:
            rank_changes_list.append({
                "run_id": run_id,
                "rank_a": pos_a,
                "rank_b": pos_b,
                "direction": "improved" if pos_b < pos_a else "deteriorated",
            })

    # overall improvement signal
    improved = (
        expectancy_improved
        and not drawdown_deteriorated
        and not (gate_a == "PASS" and gate_b == "REJECT")
    )

    return {
        "baseline_experiment_id": result_a.get("experiment_id", "unknown"),
        "candidate_experiment_id": result_b.get("experiment_id", "unknown"),
        "summary_a": sum_a,
        "summary_b": sum_b,
        "deltas": {
            "expectancy_r": expectancy_delta,
            "max_drawdown_r": drawdown_delta,
            "sample_count": sample_count_delta,
            "sample_quality_score": quality_delta,
        },
        "directions": {
            "expectancy_improved": expectancy_improved,
            "expectancy_deteriorated": expectancy_deteriorated,
            "drawdown_improved": drawdown_improved,
            "drawdown_deteriorated": drawdown_deteriorated,
        },
        "gate_status_a": gate_a,
        "gate_status_b": gate_b,
        "gate_changed": gate_changed,
        "rank_changes": rank_changes_list,
        "improved": improved,
    }
