"""Read-only hook evidence — pure frozen dataclasses, no I/O."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    hook_id: str
    operation: str
    result_status: str
    invariants_checked: List[str]
    invariants_passed: List[str]
    notes: List[str]


def build_evidence_record(
    evidence_id: str,
    hook_id: str,
    operation: str,
    result_status: str,
    invariants_checked: List[str],
    invariants_passed: List[str],
    notes: List[str],
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        hook_id=hook_id,
        operation=operation,
        result_status=result_status,
        invariants_checked=list(invariants_checked),
        invariants_passed=list(invariants_passed),
        notes=list(notes),
    )


def evidence_to_dict(record: EvidenceRecord) -> dict:
    return {
        "evidence_id": record.evidence_id,
        "hook_id": record.hook_id,
        "operation": record.operation,
        "result_status": record.result_status,
        "invariants_checked": list(record.invariants_checked),
        "invariants_passed": list(record.invariants_passed),
        "notes": list(record.notes),
    }
