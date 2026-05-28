"""Offline research experiment manifest — deterministic manifest generation.

No network. No exchange. No runtime. No planner. Advisory only.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from core.offline_research_experiment_library import (
    EXPERIMENT_LIBRARY_VERSION,
    REQUIRED_CATEGORIES,
    build_experiment_manifest,
    compute_experiment_hash,
    load_experiment_catalog,
    validate_experiment,
    validate_forbidden_commands,
)


def generate_full_manifest(catalog_path: Path) -> Dict[str, Any]:
    """Generate full manifest with validation results and hashes."""
    catalog = load_experiment_catalog(catalog_path)
    experiments = catalog["experiments"]

    validated = []
    for exp in experiments:
        errs = validate_experiment(exp)
        cmd_errs = validate_forbidden_commands(exp)
        validated.append({
            "experiment_id": exp["experiment_id"],
            "label": exp["label"],
            "category": exp.get("category", "uncategorized"),
            "hash": compute_experiment_hash(exp),
            "valid": len(errs) == 0 and len(cmd_errs) == 0,
            "errors": errs + cmd_errs,
            "safety_flags": exp["safety_flags"],
            "strategies": exp["strategy_set"],
            "symbols": exp["symbols"],
            "timeframes": exp["timeframes"],
        })

    # Sort by experiment_id for determinism
    validated.sort(key=lambda v: v["experiment_id"])

    manifest_hash = hashlib.sha256(
        json.dumps(validated, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    # Category coverage
    category_counts: Dict[str, int] = {}
    for v in validated:
        cat = v["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
    missing_categories = [c for c in REQUIRED_CATEGORIES if c not in category_counts]

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

    # Forbidden token scan summary
    forbidden_token_scan: Dict[str, int] = {}
    for exp in experiments:
        for cmd in exp.get("forbidden_commands", []):
            forbidden_token_scan[cmd] = forbidden_token_scan.get(cmd, 0) + 1

    # Expected artifact coverage
    artifact_types: Dict[str, int] = {}
    for exp in experiments:
        for art in exp.get("expected_artifact_set", []):
            artifact_types[art] = artifact_types.get(art, 0) + 1

    # Recommended review order: smoke first, then baseline, then others
    category_order = ["smoke_test", "baseline", "strategy_specific", "search_budget",
                       "timeframe", "split_mode", "symbol_universe", "robustness",
                       "negative_control", "bootstrap", "regime", "portfolio_risk",
                       "reproducibility", "report_quality", "human_review",
                       "sparse_signal", "noisy_fixture", "adverse_fixture",
                       "stress_test", "comparison_analytics"]
    recommended_review_order = []
    for cat in category_order:
        for v in validated:
            if v["category"] == cat and v["valid"]:
                recommended_review_order.append(v["experiment_id"])

    return {
        "version": "2.0.0",
        "generated_by": "offline_research_experiment_manifest",
        "experiment_library_version": EXPERIMENT_LIBRARY_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "catalog_path": str(catalog_path),
        "total_experiments": len(validated),
        "valid_experiments": sum(1 for v in validated if v["valid"]),
        "invalid_experiments": sum(1 for v in validated if not v["valid"]),
        "manifest_hash": manifest_hash,
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
        "category_counts": category_counts,
        "missing_categories": missing_categories,
        "safety_flag_summary": safety_flag_summary,
        "forbidden_token_scan": forbidden_token_scan,
        "expected_artifact_coverage": artifact_types,
        "recommended_review_order": recommended_review_order,
        "experiments": validated,
    }


def save_manifest(manifest: Dict[str, Any], output_path: Path) -> None:
    """Save manifest to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
