"""Research quality bundle — directory writer with manifest and artifact index.

No network. No exchange.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from core.research_quality_contract import RELEASE_HOLD_VALUE, SAFETY_FLAGS


def write_artifact(output_dir: Path, name: str, data: Dict) -> Path:
    """Write a single artifact to output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / name
    content = json.dumps(data, sort_keys=True, indent=2, default=str)
    path.write_text(content)
    return path


def write_bundle_skeleton(output_dir: Path, seed: int) -> Path:
    """Write initial bundle skeleton with manifest."""
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema_version": "1.0.0",
        "generated_by": "research_quality_bundle",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "quality_gate_version": "v2.0.0",
        "strict_mode": True,
        **SAFETY_FLAGS,
        "artifacts": [],
    }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2))

    index = {
        "schema_version": "1.0.0",
        "generated_by": "research_quality_bundle",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifacts": [],
    }
    index_path = output_dir / "artifact_index.json"
    index_path.write_text(json.dumps(index, sort_keys=True, indent=2))

    return manifest_path
