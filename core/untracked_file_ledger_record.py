from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UntrackedFileLedgerRecord:
    """Frozen record for a single untracked file in the ledger."""

    path: str
    state: str  # UntrackedFileState value
    risk_class: str  # UntrackedRiskClass value
    allowed_actions: tuple  # tuple of UntrackedAllowedAction values
    forbidden_actions: tuple  # tuple of UntrackedForbiddenAction values
    notes: str

    def has_allowed_action(self, action: str) -> bool:
        return action in self.allowed_actions

    def has_forbidden_action(self, action: str) -> bool:
        return action in self.forbidden_actions

    def record_to_dict(self) -> dict:
        return {
            "path": self.path,
            "state": self.state,
            "risk_class": self.risk_class,
            "allowed_actions": tuple(self.allowed_actions),
            "forbidden_actions": tuple(self.forbidden_actions),
            "notes": self.notes,
        }
