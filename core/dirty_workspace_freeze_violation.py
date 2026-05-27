from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DirtyWorkspaceFreezeViolation:
    violation_id: str
    file_path: str
    violation_type: str
    severity: str
    detected_at_slot: str

    def to_dict(self) -> dict[str, object]:
        return {
            "violation_id": self.violation_id,
            "file_path": self.file_path,
            "violation_type": self.violation_type,
            "severity": self.severity,
            "detected_at_slot": self.detected_at_slot,
        }


def build_violation(
    violation_id: str,
    file_path: str,
    violation_type: str,
    severity: str,
    detected_at_slot: str,
) -> DirtyWorkspaceFreezeViolation:
    return DirtyWorkspaceFreezeViolation(
        violation_id=violation_id,
        file_path=file_path,
        violation_type=violation_type,
        severity=severity,
        detected_at_slot=detected_at_slot,
    )


def violation_to_dict(v: DirtyWorkspaceFreezeViolation) -> dict[str, object]:
    return v.to_dict()
