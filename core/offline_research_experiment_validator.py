"""Offline research experiment validator — strict validation of experiment library.

No network. No exchange. No runtime. No planner. Advisory only.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from core.offline_research_experiment_library import (
    EXPERIMENT_LIBRARY_VERSION,
    FORBIDDEN_COMMANDS,
    FORBIDDEN_LIVE_STRINGS,
    REQUIRED_CATEGORIES,
    REQUIRED_SAFETY_FLAGS,
    VALID_SPLIT_MODES,
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
        return _build_result(
            valid=False,
            errors=[f"catalog_load_failed: {e}"],
            warnings=[],
            total=0,
            valid_count=0,
            invalid_count=0,
            category_counts={},
            experiments_raw=[],
            catalog={},
        )

    experiments = catalog.get("experiments", [])
    total = len(experiments)

    if total < min_experiments:
        errors.append(f"insufficient_experiments: {total} < {min_experiments}")

    # Duplicate ID check
    seen_ids: Dict[str, int] = {}
    for i, exp in enumerate(experiments):
        eid = exp.get("experiment_id", f"unknown_{i}")
        if eid in seen_ids:
            errors.append(f"duplicate_experiment_id: {eid}")
        seen_ids.setdefault(eid, 0)
        seen_ids[eid] += 1

    # Duplicate label check (warning)
    seen_labels: Dict[str, int] = {}
    for exp in experiments:
        lbl = exp.get("label", "")
        seen_labels.setdefault(lbl, 0)
        seen_labels[lbl] += 1
    for lbl, count in seen_labels.items():
        if count > 1:
            warnings.append(f"duplicate_label: {lbl} (appears {count} times)")

    # Per-experiment validation
    valid_count = 0
    invalid_count = 0
    for exp in experiments:
        eid = exp.get("experiment_id", "unknown")
        exp_errors = validate_experiment(exp)
        cmd_errors = validate_forbidden_commands(exp)
        all_errs = exp_errors + cmd_errors
        if all_errs:
            invalid_count += 1
            for err in all_errs:
                errors.append(f"experiment[{eid}]: {err}")
        else:
            valid_count += 1

    # Check no experiment accidentally authorizes live/testnet
    for exp in experiments:
        notes = exp.get("notes", "").lower()
        if "approve" in notes and ("live" in notes or "testnet" in notes):
            errors.append(f"experiment[{exp['experiment_id']}]: notes contain approval language")

    # Category coverage
    category_counts: Dict[str, int] = {}
    for exp in experiments:
        cat = exp.get("category", "uncategorized")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    for req_cat in REQUIRED_CATEGORIES:
        if req_cat not in category_counts:
            warnings.append(f"missing_category: {req_cat}")

    # Forbidden token scan summary
    forbidden_token_summary: Dict[str, int] = {}
    for exp in experiments:
        for cmd in exp.get("forbidden_commands", []):
            forbidden_token_summary[cmd] = forbidden_token_summary.get(cmd, 0) + 1

    # Safety flag summary
    safety_flag_summary = {
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
        "no_live": True,
        "no_submit": True,
        "no_exchange": True,
        "no_network": True,
        "no_runtime_integration": True,
        "no_planner_integration": True,
    }

    manifest = build_experiment_manifest(experiments)

    return _build_result(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        total=total,
        valid_count=valid_count,
        invalid_count=invalid_count,
        category_counts=category_counts,
        experiments_raw=experiments,
        catalog=catalog,
        manifest=manifest,
        safety_flag_summary=safety_flag_summary,
        forbidden_token_summary=forbidden_token_summary,
    )


def _build_result(
    valid: bool,
    errors: List[str],
    warnings: List[str],
    total: int,
    valid_count: int,
    invalid_count: int,
    category_counts: Dict[str, int],
    experiments_raw: List[Dict[str, Any]],
    catalog: Dict[str, Any],
    manifest: Dict[str, Any] | None = None,
    safety_flag_summary: Dict[str, Any] | None = None,
    forbidden_token_summary: Dict[str, int] | None = None,
) -> Dict[str, Any]:
    """Build machine-readable validation result."""
    result: Dict[str, Any] = {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "total_experiments": total,
        "valid_experiments": valid_count,
        "invalid_experiments": invalid_count,
        "category_counts": category_counts,
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
        "generated_by": "offline_research_experiment_validator",
        "experiment_library_version": EXPERIMENT_LIBRARY_VERSION,
        "output_hashes": {},
    }
    if manifest:
        result["manifest"] = manifest
    if safety_flag_summary:
        result["safety_flag_summary"] = safety_flag_summary
    if forbidden_token_summary:
        result["forbidden_token_summary"] = forbidden_token_summary

    # Compute output hashes
    import hashlib
    result["output_hashes"]["experiments"] = hashlib.sha256(
        json.dumps(experiments_raw, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    result["output_hashes"]["errors"] = hashlib.sha256(
        json.dumps(errors, sort_keys=True).encode()
    ).hexdigest()

    return result
