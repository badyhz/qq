"""T1444 - FrozenRiskRequirementChecklist frozen dataclass.

Pure, frozen. No I/O. No network. No random. No timestamps. No env reads.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.frozen_file_risk_requirement import FrozenFileRiskRequirement


@dataclass(frozen=True)
class FrozenRiskRequirementChecklist:
    """Immutable checklist tracking risk requirement completion.

    Pure deterministic. No I/O. No timestamps. No network.
    """
    checklist_id: str
    file_path: str
    risk_class: str
    requirements: tuple[FrozenFileRiskRequirement, ...]
    completed_count: int
    total_count: int

    @property
    def is_complete(self) -> bool:
        return self.completed_count >= self.total_count and self.total_count > 0


def build_checklist(
    checklist_id: str,
    file_path: str,
    risk_class: str,
    requirements: tuple[FrozenFileRiskRequirement, ...] = (),
    completed_count: int = 0,
) -> FrozenRiskRequirementChecklist:
    """Factory for FrozenRiskRequirementChecklist."""
    return FrozenRiskRequirementChecklist(
        checklist_id=checklist_id,
        file_path=file_path,
        risk_class=risk_class,
        requirements=requirements,
        completed_count=completed_count,
        total_count=len(requirements),
    )
