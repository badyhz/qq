"""Artifact validator. Validates runtime artifact integrity."""
from __future__ import annotations

import pathlib
from dataclasses import dataclass

from src.runtime_integrations.artifacts.artifact_manifest import ArtifactEntry


@dataclass(frozen=True)
class ValidationResult:
    total_artifacts: int
    present: int
    missing: int
    parseable: int
    unparseable: int
    all_valid: bool

    def to_dict(self) -> dict:
        return {
            "total_artifacts": self.total_artifacts,
            "present": self.present,
            "missing": self.missing,
            "parseable": self.parseable,
            "unparseable": self.unparseable,
            "all_valid": self.all_valid,
        }


def validate(entries: list[ArtifactEntry]) -> ValidationResult:
    """Validate artifact entries."""
    present = sum(1 for e in entries if e.size_bytes > 0)
    missing = sum(1 for e in entries if e.size_bytes == 0)
    parseable = sum(1 for e in entries if e.parseable and e.size_bytes > 0)
    unparseable = sum(1 for e in entries if not e.parseable and e.size_bytes > 0)
    return ValidationResult(
        total_artifacts=len(entries),
        present=present,
        missing=missing,
        parseable=parseable,
        unparseable=unparseable,
        all_valid=(missing == 0 and unparseable == 0),
    )
