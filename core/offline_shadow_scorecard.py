"""Offline shadow scorecard and grading -- pure functions.

Grades individual runs and entire experiments using quality gates.
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# quality gate thresholds
# ---------------------------------------------------------------------------

GATE_DEFAULTS: dict[str, Any] = {
    "min_candidate_count": 5,
    "min_sample_quality_score": 0.3,
    "max_drawdown_r": -5.0,  # reject if drawdown worse than this
}


# ---------------------------------------------------------------------------
# grade a single run
# ---------------------------------------------------------------------------

def grade_run(metrics: dict, gates: dict | None = None) -> dict:
    """Grade a single run's metrics.

    Parameters
    ----------
    metrics : dict
        Output of ``compute_run_metrics``.
    gates : dict, optional
        Override default gate thresholds.

    Returns
    -------
    dict
        ``grade``: PASS / WATCH / REJECT
        ``reason_codes``: list of str
        ``blockers``: list of str (only for REJECT)
    """
    g = {**GATE_DEFAULTS, **(gates or {})}

    reason_codes: list[str] = []
    blockers: list[str] = []

    candidate_count = metrics.get("candidate_count", 0)
    sample_quality = metrics.get("sample_quality_score", 0.0)
    max_dd = metrics.get("max_drawdown_r", 0.0)
    expectancy = metrics.get("expectancy_r", 0.0)

    # --- hard gates (cause REJECT) ---
    if candidate_count < g["min_candidate_count"]:
        blockers.append("insufficient_candidates")
        reason_codes.append(f"candidate_count={candidate_count}<{g['min_candidate_count']}")

    if max_dd < g["max_drawdown_r"]:
        blockers.append("drawdown_exceeded")
        reason_codes.append(f"max_drawdown_r={max_dd}<{g['max_drawdown_r']}")

    # --- soft gates (cause WATCH) ---
    if sample_quality < g["min_sample_quality_score"]:
        reason_codes.append(f"low_sample_quality={sample_quality:.4f}<{g['min_sample_quality_score']}")

    if expectancy <= 0:
        reason_codes.append(f"non_positive_expectancy={expectancy:.4f}")

    # --- assign grade ---
    if blockers:
        grade = "REJECT"
    elif expectancy > 0 and sample_quality >= g["min_sample_quality_score"]:
        grade = "PASS"
    else:
        grade = "WATCH"

    return {
        "grade": grade,
        "reason_codes": reason_codes,
        "blockers": blockers,
    }


# ---------------------------------------------------------------------------
# grade an entire experiment
# ---------------------------------------------------------------------------

def grade_experiment(results: dict) -> dict:
    """Aggregate run grades into an experiment-level verdict.

    Parameters
    ----------
    results : dict
        Output of ``evaluate_experiment`` — must have ``runs`` list.

    Returns
    -------
    dict
        ``experiment_id``, ``verdict`` (PASS/WATCH/REJECT),
        ``run_grades``: list of per-run grade dicts,
        ``pass_count``, ``watch_count``, ``reject_count``.
    """
    experiment_id = results.get("experiment_id", "unknown")
    runs = results.get("runs", [])

    run_grades: list[dict] = []
    pass_count = 0
    watch_count = 0
    reject_count = 0

    for run in runs:
        metrics = run.get("metrics", {})
        g = grade_run(metrics)
        entry = {"run_id": run.get("run_id", ""), **g}
        run_grades.append(entry)
        if g["grade"] == "PASS":
            pass_count += 1
        elif g["grade"] == "WATCH":
            watch_count += 1
        else:
            reject_count += 1

    # experiment verdict: worst of individual grades
    if reject_count > 0:
        verdict = "REJECT"
    elif watch_count > 0:
        verdict = "WATCH"
    elif pass_count > 0:
        verdict = "PASS"
    else:
        verdict = "WATCH"  # no runs -> watch

    return {
        "experiment_id": experiment_id,
        "verdict": verdict,
        "run_grades": run_grades,
        "pass_count": pass_count,
        "watch_count": watch_count,
        "reject_count": reject_count,
    }
