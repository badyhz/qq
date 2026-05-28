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
            "hash": compute_experiment_hash(exp),
            "valid": len(errs) == 0 and len(cmd_errs) == 0,
            "errors": errs + cmd_errs,
            "safety_flags": exp["safety_flags"],
            "strategies": exp["strategy_set"],
            "symbols": exp["symbols"],
            "timeframes": exp["timeframes"],
        })

    manifest_hash = hashlib.sha256(
        json.dumps(validated, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    return {
        "version": "1.0.0",
        "generated_by": "offline_research_experiment_manifest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "catalog_path": str(catalog_path),
        "total_experiments": len(validated),
        "valid_experiments": sum(1 for v in validated if v["valid"]),
        "invalid_experiments": sum(1 for v in validated if not v["valid"]),
        "manifest_hash": manifest_hash,
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
        "experiments": validated,
    }


def save_manifest(manifest: Dict[str, Any], output_path: Path) -> None:
    """Save manifest to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
