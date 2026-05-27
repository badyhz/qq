"""T1864 - Frozen Backlog Manifest Builder.

Builds a FrozenBacklogManifest from artifact file paths.
This function CAN read files (it's a builder, not a pure model),
but no network. No timestamps.
"""
from __future__ import annotations

import hashlib
import os

from core.frozen_backlog_artifact_entry import ArtifactEntry
from core.frozen_backlog_manifest import FrozenBacklogManifest


def _sha256_file(path: str) -> str:
    """Compute sha256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(
    artifact_paths: tuple[str, ...],
    generated_by: str,
) -> FrozenBacklogManifest:
    """Build a FrozenBacklogManifest from artifact file paths.

    Reads file sizes and computes sha256 hashes. No network.
    """
    entries: list[ArtifactEntry] = []
    for path in artifact_paths:
        filename = os.path.basename(path)
        size = os.path.getsize(path)
        sha = _sha256_file(path)
        entries.append(ArtifactEntry(
            filename=filename,
            size_bytes=size,
            sha256_hash=sha,
        ))

    return FrozenBacklogManifest(
        manifest_id="manifest-frozen-backlog-review",
        artifacts=tuple(entries),
        generated_by=generated_by,
        release_hold="HOLD",
        no_live=True,
        no_submit=True,
        no_exchange=True,
        no_runtime_integration=True,
        no_planner_integration=True,
    )
