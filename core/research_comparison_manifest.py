"""Research comparison manifest — build comparison manifest.

Program I: Comparison Manifest.
Emit research_comparison_manifest.json with all safety flags.

No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


COMPARISON_VERSION = "1.0.0"
COMPARISON_GENERATED_BY = "research_comparison_analytics"


def build_comparison_manifest(
    bundle_labels: Tuple[str, ...],
    bundle_hashes: Dict[str, str],
    output_artifact_hashes: Dict[str, str],
    deterministic_seed: Optional[int] = None,
    generated_at: str = "deterministic",
    strict_mode: bool = True,
) -> Dict[str, Any]:
    """Build comparison manifest with all safety flags."""
    manifest: Dict[str, Any] = {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "generated_by": COMPARISON_GENERATED_BY,
        "comparison_version": COMPARISON_VERSION,
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
        "no_live": True,
        "no_submit": True,
        "no_exchange": True,
        "no_network": True,
        "no_runtime_integration": True,
        "no_planner_integration": True,
        "strict_mode": strict_mode,
        "bundle_labels": list(bundle_labels),
        "input_bundle_hashes": bundle_hashes,
        "output_artifact_hashes": output_artifact_hashes,
    }

    if deterministic_seed is not None:
        manifest["deterministic_seed"] = deterministic_seed

    return manifest


def compute_output_artifact_hashes(
    output_dir: Path,
    artifact_names: Tuple[str, ...],
) -> Dict[str, str]:
    """Compute SHA256 hashes for output artifacts."""
    hashes: Dict[str, str] = {}
    for name in sorted(artifact_names):
        p = output_dir / name
        if p.exists():
            try:
                raw = p.read_bytes()
                hashes[name] = hashlib.sha256(raw).hexdigest()
            except OSError:
                pass
    return hashes


def compute_bundle_hashes(
    records: Tuple[Any, ...],
) -> Dict[str, str]:
    """Compute bundle hashes from records."""
    hashes: Dict[str, str] = {}
    for r in records:
        hashes[r.label] = hashlib.sha256(
            json.dumps(r.artifact_hashes, sort_keys=True).encode()
        ).hexdigest()
    return hashes


def validate_manifest_safety(manifest: Dict[str, Any]) -> Tuple[bool, Tuple[str, ...]]:
    """Validate manifest safety flags. Returns (valid, errors)."""
    errors: List[str] = []

    checks = {
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

    for key, expected in checks.items():
        actual = manifest.get(key)
        if actual != expected:
            errors.append(f"{key}={actual!r}, expected {expected!r}")

    return (len(errors) == 0, tuple(errors))
