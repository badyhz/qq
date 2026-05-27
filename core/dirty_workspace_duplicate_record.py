from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DirtyWorkspaceDuplicateRecord:
    canonical_path: str
    duplicate_path: str
    category: str
    action: str

    def to_dict(self) -> dict[str, object]:
        return {
            "canonical_path": self.canonical_path,
            "duplicate_path": self.duplicate_path,
            "category": self.category,
            "action": self.action,
        }


def build_duplicate_record(
    canonical_path: str,
    duplicate_path: str,
    category: str,
    action: str,
) -> DirtyWorkspaceDuplicateRecord:
    return DirtyWorkspaceDuplicateRecord(
        canonical_path=canonical_path,
        duplicate_path=duplicate_path,
        category=category,
        action=action,
    )
