"""T1305 - Frozen Backlog Evidence Requirement."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrozenBacklogEvidenceRequirement:
    """Immutable evidence requirement.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    requirement_id: str
    evidence_type: str
    required_fields: tuple[str, ...]
    mandatory: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "requirement_id": self.requirement_id,
            "evidence_type": self.evidence_type,
            "required_fields": self.required_fields,
            "mandatory": self.mandatory,
        }


def build_evidence_requirement(
    requirement_id: str,
    evidence_type: str,
    required_fields: tuple[str, ...] = (),
    mandatory: bool = True,
) -> FrozenBacklogEvidenceRequirement:
    """Factory for FrozenBacklogEvidenceRequirement."""
    return FrozenBacklogEvidenceRequirement(
        requirement_id=requirement_id,
        evidence_type=evidence_type,
        required_fields=required_fields,
        mandatory=mandatory,
    )


def evidence_requirement_to_dict(
    r: FrozenBacklogEvidenceRequirement,
) -> dict[str, object]:
    """Convert evidence requirement to a plain dict."""
    return r.to_dict()
