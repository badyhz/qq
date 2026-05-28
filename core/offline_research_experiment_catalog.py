"""Offline research experiment catalog — load and index experiment definitions.

No network. No exchange. No runtime. No planner. Advisory only.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.offline_research_experiment_library import (
    load_experiment_catalog,
    validate_experiment,
    validate_forbidden_commands,
    compute_experiment_hash,
    build_experiment_manifest,
)


def load_and_validate_catalog(catalog_path: Path) -> Dict[str, Any]:
    """Load catalog and validate all experiments. Returns result dict."""
    catalog = load_experiment_catalog(catalog_path)
    experiments = catalog["experiments"]
    results = []
    all_errors = []
    for i, exp in enumerate(experiments):
        errs = validate_experiment(exp)
        cmd_errs = validate_forbidden_commands(exp)
        all_exp_errs = errs + cmd_errs
        results.append({
            "experiment_id": exp.get("experiment_id", f"unknown_{i}"),
            "errors": all_exp_errs,
            "valid": len(all_exp_errs) == 0,
        })
        all_errors.extend(all_exp_errs)

    return {
        "catalog_path": str(catalog_path),
        "total_experiments": len(experiments),
        "valid_experiments": sum(1 for r in results if r["valid"]),
        "invalid_experiments": sum(1 for r in results if not r["valid"]),
        "results": results,
        "all_errors": all_errors,
        "valid": len(all_errors) == 0,
    }


def get_experiment_ids(catalog_path: Path) -> List[str]:
    """Get list of experiment IDs from catalog."""
    catalog = load_experiment_catalog(catalog_path)
    return [e["experiment_id"] for e in catalog["experiments"]]


def get_experiment_by_id(catalog_path: Path, experiment_id: str) -> Optional[Dict[str, Any]]:
    """Get a single experiment by ID."""
    catalog = load_experiment_catalog(catalog_path)
    for exp in catalog["experiments"]:
        if exp["experiment_id"] == experiment_id:
            return exp
    return None


def build_command_preview(experiment: Dict[str, Any]) -> List[str]:
    """Build offline-only command preview for an experiment."""
    exp_id = experiment["experiment_id"]
    strategies = ",".join(experiment["strategy_set"])
    symbols = ",".join(experiment["symbols"])
    timeframes = ",".join(experiment["timeframes"])
    split_mode = experiment["split_mode"]
    budget = experiment["search_budget"]
    chunk = experiment["chunk_size"]
    seed = experiment["deterministic_seed"]

    commands = [
        (
            f"python3 scripts/run_multi_strategy_research_workbench.py "
            f"--fixture-dir tests/fixtures/historical_backtest_lab "
            f"--output-dir /tmp/offline_exp_{exp_id} "
            f"--strategies {strategies} "
            f"--symbols {symbols} "
            f"--timeframes {timeframes} "
            f"--split-mode {split_mode} "
            f"--search-budget {budget} "
            f"--chunk-size {chunk}"
        ),
        (
            f"python3 scripts/run_multi_strategy_research_quality_gate.py "
            f"--input-dir /tmp/offline_exp_{exp_id} "
            f"--output-dir /tmp/offline_exp_{exp_id}_quality "
            f"--deterministic-seed {seed} "
            f"--strict --release-hold HOLD"
        ),
        (
            f"python3 scripts/build_research_artifact_browser.py "
            f"--quality-dir /tmp/offline_exp_{exp_id}_quality "
            f"--output-dir /tmp/offline_exp_{exp_id}_browser "
            f"--strict --release-hold HOLD"
        ),
    ]
    return commands
