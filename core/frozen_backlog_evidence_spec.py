"""T1374 - Frozen Backlog Evidence Spec."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrozenBacklogEvidenceSpec:
    """Immutable evidence specification.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    spec_id: str
    evidence_type: str
    required_fields: tuple[str, ...]
    format: str
    mandatory: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "spec_id": self.spec_id,
            "evidence_type": self.evidence_type,
            "required_fields": self.required_fields,
            "format": self.format,
            "mandatory": self.mandatory,
        }


def build_evidence_spec(
    spec_id: str,
    evidence_type: str,
    required_fields: tuple[str, ...] = (),
    format: str = "json",
    mandatory: bool = True,
) -> FrozenBacklogEvidenceSpec:
    """Factory for FrozenBacklogEvidenceSpec."""
    return FrozenBacklogEvidenceSpec(
        spec_id=spec_id,
        evidence_type=evidence_type,
        required_fields=required_fields,
        format=format,
        mandatory=mandatory,
    )
