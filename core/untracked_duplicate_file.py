from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UntrackedDuplicateFile:
    """Frozen record for a duplicate untracked file."""

    canonical_path: str
    duplicate_path: str
    content_hash: str  # SHA-256 hex digest
    recommended_action: str  # e.g. "KEEP_CANONICAL", "KEEP_DUPLICATE", "KEEP_BOTH", "DEFER"

    def is_self_referencing(self) -> bool:
        """Return True if canonical and duplicate are the same path."""
        return self.canonical_path == self.duplicate_path

    def duplicate_to_dict(self) -> dict:
        return {
            "canonical_path": self.canonical_path,
            "duplicate_path": self.duplicate_path,
            "content_hash": self.content_hash,
            "recommended_action": self.recommended_action,
        }
