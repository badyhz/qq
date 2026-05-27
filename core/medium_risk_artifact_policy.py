from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediumRiskArtifactPolicy:
    """T1216 - frozen dataclass for artifact output policy."""

    allowed_dirs: tuple[str, ...]
    forbidden_dirs: tuple[str, ...]
    requires_human_review: bool
