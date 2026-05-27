from __future__ import annotations

from dataclasses import dataclass

from core.dirty_workspace_duplicate_record import DirtyWorkspaceDuplicateRecord
from core.dirty_workspace_freeze_violation import DirtyWorkspaceFreezeViolation


@dataclass(frozen=True)
class DirtyWorkspaceGovernanceVerdict:
    verdict: str
    violations: tuple[DirtyWorkspaceFreezeViolation, ...]
    duplicates: tuple[DirtyWorkspaceDuplicateRecord, ...]
    notes: str

    def to_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict,
            "violations": tuple(v.to_dict() for v in self.violations),
            "duplicates": tuple(d.to_dict() for d in self.duplicates),
            "notes": self.notes,
        }


def build_verdict(
    verdict: str,
    violations: tuple[DirtyWorkspaceFreezeViolation, ...],
    duplicates: tuple[DirtyWorkspaceDuplicateRecord, ...],
    notes: str,
) -> DirtyWorkspaceGovernanceVerdict:
    valid_verdicts = ("PASS", "FAIL", "BLOCKED", "HOLD")
    if verdict not in valid_verdicts:
        verdict = "BLOCKED"
    return DirtyWorkspaceGovernanceVerdict(
        verdict=verdict,
        violations=violations,
        duplicates=duplicates,
        notes=notes,
    )


def verdict_to_dict(v: DirtyWorkspaceGovernanceVerdict) -> dict[str, object]:
    return v.to_dict()
