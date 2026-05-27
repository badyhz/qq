"""T1340 - Human approval evidence verdict with validation."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumanApprovalEvidenceVerdict:
    """Immutable verdict issued after reviewing an evidence pack."""

    verdict: str
    notes: str
    missing_fields: tuple[str, ...]
    approved_by: str

    def to_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict,
            "notes": self.notes,
            "missing_fields": list(self.missing_fields),
            "approved_by": self.approved_by,
        }

    def is_approved(self) -> bool:
        return self.verdict.upper() == "APPROVED"

    def has_missing_fields(self) -> bool:
        return len(self.missing_fields) > 0


def build_verdict(
    verdict: str,
    notes: str,
    missing_fields: tuple[str, ...],
    approved_by: str,
) -> HumanApprovalEvidenceVerdict:
    """Build a verdict after validation.

    Rules:
    - verdict must be one of APPROVED / REJECTED / HOLD
    - approved_by must be non-empty
    - REJECTED verdict requires non-empty notes
    - APPROVED verdict requires empty missing_fields

    Raises ValueError on violation.
    """
    allowed = {"APPROVED", "REJECTED", "HOLD"}
    if verdict.upper() not in allowed:
        raise ValueError(f"verdict must be one of {allowed}, got {verdict!r}")
    if not approved_by.strip():
        raise ValueError("approved_by must be non-empty")
    if verdict.upper() == "REJECTED" and not notes.strip():
        raise ValueError("REJECTED verdict requires non-empty notes")
    if verdict.upper() == "APPROVED" and len(missing_fields) > 0:
        raise ValueError("APPROVED verdict cannot have missing_fields")
    return HumanApprovalEvidenceVerdict(
        verdict=verdict,
        notes=notes,
        missing_fields=missing_fields,
        approved_by=approved_by,
    )
