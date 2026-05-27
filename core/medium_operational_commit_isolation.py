"""T1318 — Medium operational commit isolation model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediumOperationalCommitIsolation:
    """Declares commit isolation requirements for medium-risk scripts."""

    isolation_id: str
    script_name: str
    must_commit_alone: bool
    related_files: tuple[str, ...]

    def related_count(self) -> int:
        return len(self.related_files)

    def related_set(self) -> frozenset[str]:
        return frozenset(self.related_files)

    def is_isolated(self) -> bool:
        return self.must_commit_alone

    def has_related_files(self) -> bool:
        return len(self.related_files) > 0

    def requires_solo_commit(self) -> bool:
        return self.must_commit_alone and len(self.related_files) == 0
