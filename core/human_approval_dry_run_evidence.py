"""T1338 - Human approval dry-run evidence."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumanApprovalDryRunEvidence:
    """Immutable evidence that a dry-run produced expected results."""

    evidence_id: str
    dry_run_result: str
    expected_behavior: str
    match_status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id,
            "dry_run_result": self.dry_run_result,
            "expected_behavior": self.expected_behavior,
            "match_status": self.match_status,
        }

    def is_match(self) -> bool:
        return self.match_status.upper() == "MATCH"
