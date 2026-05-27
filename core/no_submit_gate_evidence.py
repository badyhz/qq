from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NoSubmitGateEvidence:
    evidence_id: str
    check_name: str
    passed: bool
    details: str


def build_evidence(
    evidence_id: str,
    check_name: str,
    passed: bool,
    details: str,
) -> NoSubmitGateEvidence:
    return NoSubmitGateEvidence(
        evidence_id=evidence_id,
        check_name=check_name,
        passed=passed,
        details=details,
    )
