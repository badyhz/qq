from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DirtyWorkspaceFileRecord:
    path: str
    tracked: bool
    category: str
    risk_level: str
    action: str
    notes: str

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "tracked": self.tracked,
            "category": self.category,
            "risk_level": self.risk_level,
            "action": self.action,
            "notes": self.notes,
        }
