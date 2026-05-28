"""Offline research experiment validator — strict validation of experiment library.

No network. No exchange. No runtime. No planner. Advisory only.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from core.offline_research_experiment_library import (
    FORBIDDEN_COMMANDS,
    FORBIDDEN_LIVE_STRINGS,
    REQUIRED_SAFETY_FLAGS,
    build_experiment_manifest,
    check_forbidden_strings,
    compute_experiment_hash,
    load_experiment_catalog,
    validate_experiment,
    validate_forbidden_commands,
)

RELEASE_HOLD_VALUE = "HOLD"


def validate_catalog_strict(
    catalog_path: Path,
    release_hold: str = "HOLD",
    min_experiments: int = 20,
) -> Dict[str, Any]:
    """Strict validation of entire experiment catalog."""
    errors: List[str] = []
    warnings: List[str] = []

    if release_hold != RELEASE_HOLD_VALUE:
        errors.append(f"release_hold mismatch: expected HOLD, got {release_hold}")

    try:
        catalog = load_experiment_catalog(catalog_path)
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"catalog_load_failed: {e}"],
            "warnings": [],
            "total_experiments": 0,
        }

    experiments = catalog.get("experiments", [])
    if len(experiments) < min_experiments:
        errors.append(f"insufficient_experiments: {len(experiments)} < {min_experiments}")

    seen_ids = set()
    for i, exp in enumerate(experiments):
        eid = exp.get("experiment_id", f"unknown_{i}")
        if eid in seen_ids:
            errors.append(f"duplicate_experiment_id: {eid}")
        seen_ids.add(eid)

        exp_errors = validate_experiment(exp)
        cmd_errors = validate_forbidden_commands(exp)
        all_errs = exp_errors + cmd_errors
        for err in all_errs:
            errors.append(f"experiment[{eid}]: {err}")

    # Check no experiment accidentally authorizes live/testnet
    for exp in experiments:
        notes = exp.get("notes", "").lower()
        if "approve" in notes and ("live" in notes or "testnet" in notes):
            errors.append(f"experiment[{exp['experiment_id']}]: notes contain approval language")

    manifest = build_experiment_manifest(experiments)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "total_experiments": len(experiments),
        "manifest": manifest,
    }
