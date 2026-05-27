"""Offline shadow experiment evaluator -- pure function.

Takes a matrix dict (list of run specs) and a fixture directory,
loads outcome files for each run, computes metrics, returns results.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.offline_shadow_metric_engine import compute_run_metrics


def _load_outcomes(fixture_dir: str, run_id: str) -> list[dict]:
    """Load outcome records from ``<fixture_dir>/<run_id>.json``.

    Returns empty list if file not found or invalid.
    """
    path = Path(fixture_dir) / f"{run_id}.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "outcomes" in data:
            return data["outcomes"]
        return []
    except (json.JSONDecodeError, OSError):
        return []


def evaluate_experiment(matrix: dict, fixture_dir: str) -> dict:
    """Evaluate all runs in an experiment matrix.

    Parameters
    ----------
    matrix : dict
        Must contain ``"runs"`` key with a list of run spec dicts.
        Each run spec must have a ``"run_id"`` (str).
    fixture_dir : str
        Path to directory containing per-run outcome JSON files.

    Returns
    -------
    dict
        ``{"experiment_id": str, "run_count": int, "runs": list[dict]}``
        Each run entry has ``run_id``, ``metrics``, ``outcome_count``.
    """
    runs_in = matrix.get("runs", [])
    experiment_id = matrix.get("experiment_id", "unknown")

    runs_out: list[dict] = []
    for run_spec in runs_in:
        run_id = run_spec.get("run_id", "")
        outcomes = _load_outcomes(fixture_dir, run_id)
        metrics = compute_run_metrics(outcomes)
        runs_out.append({
            "run_id": run_id,
            "outcome_count": len(outcomes),
            "metrics": metrics,
        })

    return {
        "experiment_id": experiment_id,
        "run_count": len(runs_out),
        "runs": runs_out,
    }
