"""Research reproducibility manifest — manifest with all safety flags.

No network.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict

from core.research_quality_contract import RELEASE_HOLD_VALUE, SAFETY_FLAGS


def build_reproducibility_manifest(
    seed: int,
    input_hashes: Dict[str, str],
    output_hashes: Dict[str, str],
    quality_gate_version: str = "v2.0.0",
    strict: bool = True,
    generated_at: str = None,
) -> Dict:
    """Build reproducibility_manifest.json."""
    return {
        "schema_version": "1.0.0",
        "generated_by": "research_reproducibility",
        "generated_at": generated_at or f"seed_{seed}",
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "quality_gate_version": quality_gate_version,
        "strict_mode": strict,
        "no_live": SAFETY_FLAGS["no_live"],
        "no_submit": SAFETY_FLAGS["no_submit"],
        "no_exchange": SAFETY_FLAGS["no_exchange"],
        "no_runtime_integration": SAFETY_FLAGS["no_runtime_integration"],
        "no_planner_integration": SAFETY_FLAGS["no_planner_integration"],
        "no_network": SAFETY_FLAGS["no_network"],
        "input_artifact_hashes": input_hashes,
        "output_artifact_hashes": output_hashes,
    }
