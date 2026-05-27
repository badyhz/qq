"""T1863 - Frozen Backlog Artifact Entry.

Frozen dataclass for a single artifact in a manifest.
Pure deterministic. No I/O. No timestamps. No network.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArtifactEntry:
    """Immutable entry for a single artifact in a manifest.

    Pure frozen. No I/O. No timestamps. No network.
    """

    filename: str
    size_bytes: int
    sha256_hash: str

    def to_dict(self) -> dict[str, object]:
        return {
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "sha256_hash": self.sha256_hash,
        }
