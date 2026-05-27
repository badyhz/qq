"""Research artifact index — enumerate, hash, validate artifacts.

No network, no exchange, no remote URIs.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class ArtifactEntry:
    """A single artifact index entry."""
    artifact_id: str
    artifact_type: str
    path: str
    sha256: str
    size_bytes: int
    related_strategy: str = None
    related_experiment: str = None
    related_matrix_row: str = None
    created_by: str = "multi_strategy_research_workbench"
    release_hold: str = "HOLD"
    safety_flags: Dict[str, bool] = None


@dataclass(frozen=True)
class ArtifactIndex:
    """Complete artifact index."""
    artifact_index_id: str
    artifacts: Tuple[ArtifactEntry, ...]


ARTIFACT_TYPES = {
    "strategy_registry.json": "strategy_registry",
    "parameter_search.json": "parameter_search",
    "matrix.json": "matrix",
    "results.json": "results",
    "portfolio_summary.json": "portfolio_summary",
    "comparison.json": "comparison",
    "promotion_recommendations.json": "promotion_recommendations",
    "artifact_index.json": "artifact_index",
    "report.md": "report_md",
    "report.html": "report_html",
    "manifest.json": "manifest",
}

FORBIDDEN_PATHS = frozenset({
    "core/live_runner.py",
    "scripts/live_playbook.py",
    "scripts/submit_approved_candidates.py",
    "scripts/run_testnet_order_smoke.py",
    "scripts/run_signal_testnet_trial.py",
    "scripts/run_spot_testnet_acceptance.py",
    "scripts/safe_flatten_testnet_symbol.py",
})


def _compute_sha256(path: Path) -> str:
    """Compute SHA256 of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_artifact_index(
    output_dir: Path,
    created_by: str = "multi_strategy_research_workbench",
) -> ArtifactIndex:
    """Build artifact index from output directory.

    Validates that all paths are local, no forbidden paths.
    """
    artifacts: List[ArtifactEntry] = []
    counter = 0

    for filename, artifact_type in sorted(ARTIFACT_TYPES.items()):
        filepath = output_dir / filename
        if not filepath.exists():
            continue

        # Validate path is local
        path_str = str(filepath)
        for forbidden in FORBIDDEN_PATHS:
            if forbidden in path_str:
                raise ValueError(f"forbidden path detected: {path_str}")

        counter += 1
        sha = _compute_sha256(filepath)
        size = filepath.stat().st_size

        artifacts.append(ArtifactEntry(
            artifact_id=f"artifact_{counter:06d}",
            artifact_type=artifact_type,
            path=str(filepath),
            sha256=sha,
            size_bytes=size,
            created_by=created_by,
        ))

    return ArtifactIndex(
        artifact_index_id="artifact_index_001",
        artifacts=tuple(artifacts),
    )


def validate_artifact_index(index: ArtifactIndex) -> List[str]:
    """Validate artifact index. Returns list of errors."""
    errors: List[str] = []
    for entry in index.artifacts:
        if not entry.path:
            errors.append(f"artifact {entry.artifact_id}: missing path")
        if entry.path and ("http://" in entry.path or "https://" in entry.path):
            errors.append(f"artifact {entry.artifact_id}: remote URI detected")
        if entry.release_hold != "HOLD":
            errors.append(f"artifact {entry.artifact_id}: release_hold != HOLD")
        for forbidden in FORBIDDEN_PATHS:
            if forbidden in (entry.path or ""):
                errors.append(f"artifact {entry.artifact_id}: forbidden path")
    return errors


def artifact_index_to_dict(index: ArtifactIndex) -> Dict[str, Any]:
    """Serialize to dict."""
    return {
        "artifact_index_id": index.artifact_index_id,
        "artifacts": [
            {
                "artifact_id": a.artifact_id,
                "artifact_type": a.artifact_type,
                "path": a.path,
                "sha256": a.sha256,
                "size_bytes": a.size_bytes,
                "related_strategy": a.related_strategy,
                "related_experiment": a.related_experiment,
                "created_by": a.created_by,
                "release_hold": a.release_hold,
                "safety_flags": a.safety_flags or {},
            }
            for a in index.artifacts
        ],
    }


def artifact_index_to_json(index: ArtifactIndex, indent: int = 2) -> str:
    """Serialize to JSON."""
    return json.dumps(artifact_index_to_dict(index), sort_keys=True, indent=indent)
