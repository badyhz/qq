from __future__ import annotations

from dataclasses import dataclass

from core.dirty_workspace_file_record import DirtyWorkspaceFileRecord


@dataclass(frozen=True)
class DirtyWorkspaceClassificationResult:
    total_files: int
    records: tuple[DirtyWorkspaceFileRecord, ...]
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "total_files": self.total_files,
            "records": tuple(r.to_dict() for r in self.records),
            "high_risk_count": self.high_risk_count,
            "medium_risk_count": self.medium_risk_count,
            "low_risk_count": self.low_risk_count,
        }


def build_classification_result(file_dicts: list[dict[str, object]]) -> DirtyWorkspaceClassificationResult:
    """Build a classification result from a list of file dicts.

    Each dict must contain: path, tracked, category, risk_level, action, notes.
    """
    records = tuple(
        DirtyWorkspaceFileRecord(
            path=str(d.get("path", "")),
            tracked=bool(d.get("tracked", False)),
            category=str(d.get("category", "G_HUMAN_DECISION")),
            risk_level=str(d.get("risk_level", "HIGH")),
            action=str(d.get("action", "HUMAN_REVIEW_ONLY")),
            notes=str(d.get("notes", "")),
        )
        for d in file_dicts
    )
    high = sum(1 for r in records if r.risk_level == "HIGH")
    medium = sum(1 for r in records if r.risk_level == "MEDIUM")
    low = sum(1 for r in records if r.risk_level == "LOW")
    return DirtyWorkspaceClassificationResult(
        total_files=len(records),
        records=records,
        high_risk_count=high,
        medium_risk_count=medium,
        low_risk_count=low,
    )
