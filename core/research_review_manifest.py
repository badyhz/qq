"""Research review manifest.

Program H: Review Manifest.
Generates review_manifest.json with all safety flags.

No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Tuple

REVIEW_MANIFEST_VERSION = "1.0.0"


def build_review_manifest(
    source_hashes: Dict[str, str],
    output_hashes: Dict[str, str],
    generated_by: str = "research_human_review",
    generated_at: str = "deterministic",
    strict_mode: bool = True,
) -> Dict[str, Any]:
    """Build review manifest with all safety flags."""
    return {
        "schema_version": "1.0.0",
        "manifest_version": REVIEW_MANIFEST_VERSION,
        "generated_at": generated_at,
        "generated_by": generated_by,
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
        "review_workflow_version": REVIEW_MANIFEST_VERSION,
        "source_hashes": source_hashes,
        "output_hashes": output_hashes,
    }


def validate_review_manifest_safety(manifest: Dict[str, Any]) -> Tuple[bool, Tuple[str, ...]]:
    """Validate review manifest safety flags."""
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
