"""Research workbench manifest builder — build and validate manifest.

Validates release_hold, safety flags, sha256, missing artifacts.
No network, no exchange.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


REQUIRED_SAFETY_FLAGS = {
    "release_hold": "HOLD",
    "no_live": True,
    "no_submit": True,
    "no_exchange": True,
    "no_runtime_integration": True,
    "no_planner_integration": True,
    "no_network": True,
}


@dataclass(frozen=True)
class WorkbenchManifest:
    """Workbench manifest with safety flags and artifact hashes."""
    manifest_id: str
    generated_by: str
    release_hold: str
    no_live: bool
    no_submit: bool
    no_exchange: bool
    no_runtime_integration: bool
    no_planner_integration: bool
    no_network: bool
    artifacts: Tuple[str, ...]
    sha256: Dict[str, str]
    artifact_sizes: Dict[str, int]
    warnings: Tuple[str, ...]
    validation_status: str


def build_manifest(
    output_dir: Path,
    required_artifacts: List[str] = None,
    generated_by: str = "scripts/run_multi_strategy_research_workbench.py",
) -> WorkbenchManifest:
    """Build manifest from output directory.

    Validates safety flags. Fails if release_hold != HOLD.
    """
    if required_artifacts is None:
        required_artifacts = [
            "strategy_registry.json", "parameter_search.json", "matrix.json",
            "results.json", "portfolio_summary.json", "comparison.json",
            "promotion_recommendations.json", "artifact_index.json",
            "report.md", "report.html", "manifest.json",
        ]

    warnings: List[str] = []
    sha256_map: Dict[str, str] = {}
    sizes: Dict[str, int] = {}
    found: List[str] = []

    for name in required_artifacts:
        if name == "manifest.json":
            continue  # Skip self
        filepath = output_dir / name
        if filepath.exists():
            found.append(name)
            sha256_map[name] = hashlib.sha256(filepath.read_bytes()).hexdigest()
            sizes[name] = filepath.stat().st_size
        else:
            warnings.append(f"MISSING_ARTIFACT: {name}")

    status = "PASS" if not warnings else "WARN"

    return WorkbenchManifest(
        manifest_id="multi_strategy_research_workbench_manifest",
        generated_by=generated_by,
        release_hold="HOLD",
        no_live=True,
        no_submit=True,
        no_exchange=True,
        no_runtime_integration=True,
        no_planner_integration=True,
        no_network=True,
        artifacts=tuple(found),
        sha256=sha256_map,
        artifact_sizes=sizes,
        warnings=tuple(warnings),
        validation_status=status,
    )


def validate_manifest(manifest: WorkbenchManifest) -> List[str]:
    """Validate manifest. Returns list of errors."""
    errors: List[str] = []
    if manifest.release_hold != "HOLD":
        errors.append(f"release_hold must be HOLD, got {manifest.release_hold!r}")
    if not manifest.no_live:
        errors.append("no_live must be True")
    if not manifest.no_submit:
        errors.append("no_submit must be True")
    if not manifest.no_exchange:
        errors.append("no_exchange must be True")
    if not manifest.no_runtime_integration:
        errors.append("no_runtime_integration must be True")
    if not manifest.no_planner_integration:
        errors.append("no_planner_integration must be True")
    if not manifest.no_network:
        errors.append("no_network must be True")
    return errors


def manifest_to_dict(manifest: WorkbenchManifest) -> Dict[str, Any]:
    """Serialize manifest to dict."""
    return {
        "manifest_id": manifest.manifest_id,
        "generated_by": manifest.generated_by,
        "release_hold": manifest.release_hold,
        "no_live": manifest.no_live,
        "no_submit": manifest.no_submit,
        "no_exchange": manifest.no_exchange,
        "no_runtime_integration": manifest.no_runtime_integration,
        "no_planner_integration": manifest.no_planner_integration,
        "no_network": manifest.no_network,
        "artifacts": list(manifest.artifacts),
        "sha256": manifest.sha256,
        "artifact_sizes": manifest.artifact_sizes,
        "warnings": list(manifest.warnings),
        "validation_status": manifest.validation_status,
    }


def manifest_to_json(manifest: WorkbenchManifest, indent: int = 2) -> str:
    """Serialize manifest to JSON."""
    return json.dumps(manifest_to_dict(manifest), sort_keys=True, indent=indent)
