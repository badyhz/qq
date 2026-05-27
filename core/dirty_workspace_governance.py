from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DirtyWorkspaceGovernance:
    policy_version: str
    file_categories: tuple[str, ...]
    risk_levels: tuple[str, ...]
    enforcement_mode: str

    def describe(self) -> dict[str, object]:
        return {
            "policy_version": self.policy_version,
            "file_categories": self.file_categories,
            "risk_levels": self.risk_levels,
            "enforcement_mode": self.enforcement_mode,
        }
