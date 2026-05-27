"""T1331 - Human approval evidence pack."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumanApprovalEvidencePack:
    """Immutable container grouping all evidence fields for a single approval."""

    pack_id: str
    fields: tuple[str, ...]
    reviewer: str
    verdict: str

    def to_dict(self) -> dict[str, object]:
        return {
            "pack_id": self.pack_id,
            "fields": list(self.fields),
            "reviewer": self.reviewer,
            "verdict": self.verdict,
        }

    def has_field(self, field_id: str) -> bool:
        return field_id in self.fields

    def field_count(self) -> int:
        return len(self.fields)
